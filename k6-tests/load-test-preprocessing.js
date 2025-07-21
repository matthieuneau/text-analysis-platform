import { check, sleep } from 'k6';
import http from 'k6/http';
import { Counter, Rate, Trend } from 'k6/metrics';

// Custom metrics
const httpReqFailed = new Rate('http_req_failed');
const httpReqDuration = new Trend('http_req_duration', true);
const endpointCounter = new Counter('endpoint_requests');
const textSizeCounter = new Counter('text_size_requests');

// Configuration
const BASE_URL = __ENV.BASE_URL || 'http://localhost:8001';

// Load test configuration
const config = {
  // Text size distribution (must sum to 100)
  textDistribution: {
    short: parseInt(__ENV.SHORT_PERCENT || '40'),    // 40% short texts
    medium: parseInt(__ENV.MEDIUM_PERCENT || '40'),   // 40% medium texts  
    long: parseInt(__ENV.LONG_PERCENT || '20')        // 20% long texts
  },
  
  // Endpoint distribution (must sum to 100)
  endpointDistribution: {
    clean: parseInt(__ENV.CLEAN_PERCENT || '50'),      // 50% /clean requests
    tokenize: parseInt(__ENV.TOKENIZE_PERCENT || '30'), // 30% /tokenize requests
    normalize: parseInt(__ENV.NORMALIZE_PERCENT || '20') // 20% /normalize requests
  },
  
  // Cache behavior
  cacheHitRate: parseFloat(__ENV.CACHE_HIT_RATE || '0'), // No cache hits for now

  // Request options variation
  optionVariation: parseFloat(__ENV.OPTION_VARIATION || '0.7') // 70% requests use custom options
};

// Validate distributions sum to 100
function validateDistribution(dist, name) {
  const sum = Object.values(dist).reduce((a, b) => a + b, 0);
  if (sum !== 100) {
    throw new Error(`${name} distribution must sum to 100, got ${sum}`);
  }
}

validateDistribution(config.textDistribution, 'Text size');
validateDistribution(config.endpointDistribution, 'Endpoint');

// Load datasets
const datasets = {
  short: [],
  medium: [],
  long: []
};

// Load dataset files
function loadDataset(filename) {
  const file = open(`./datasets/${filename}`);
  return file.split('\n')
    .filter(line => line.trim())
    .map(line => JSON.parse(line));
}

// Initialize datasets
datasets.short = loadDataset('short.jsonl');
datasets.medium = loadDataset('medium.jsonl');  
datasets.long = loadDataset('long.jsonl');

console.log(`Loaded datasets: ${datasets.short.length} short, ${datasets.medium.length} medium, ${datasets.long.length} long texts`);

// Test options configurations
const testOptions = [
  // Default options (minimal processing)
  {},
  
  // Aggressive cleaning
  {
    remove_urls: true,
    remove_emails: true,
    remove_special_chars: true,
    remove_numbers: true,
    remove_extra_whitespace: true
  },
  
  // Normalization focused
  {
    lowercase: true,
    remove_punctuation: true,
    remove_extra_whitespace: true
  },
  
  // Light processing
  {
    remove_urls: true,
    remove_emails: true,
    remove_extra_whitespace: true
  },
  
  // Tokenization specific
  {
    split_punctuation: true,
    lowercase: true
  }
];

// Weighted random selection
function weightedRandomSelect(distribution) {
  const rand = Math.random() * 100;
  let cumulative = 0;
  
  for (const [key, weight] of Object.entries(distribution)) {
    cumulative += weight;
    if (rand <= cumulative) {
      return key;
    }
  }
  
  // Fallback to first option
  return Object.keys(distribution)[0];
}

// Get random text from selected size category
function getRandomText(sizeCategory) {
  const texts = datasets[sizeCategory];
  const randomIndex = Math.floor(Math.random() * texts.length);
  return texts[randomIndex];
}

// Get random test options
function getRandomOptions() {
  if (Math.random() > config.optionVariation) {
    return {}; // Default options
  }
  
  const randomIndex = Math.floor(Math.random() * testOptions.length);
  return testOptions[randomIndex];
}

// Cache simulation - reuse some texts to test caching
const recentTexts = [];
const maxRecentTexts = 100;

function getTextForRequest(sizeCategory) {
  // Simulate cache hits by occasionally reusing recent texts
  if (Math.random() < config.cacheHitRate && recentTexts.length > 0) {
    const randomIndex = Math.floor(Math.random() * recentTexts.length);
    return recentTexts[randomIndex];
  }
  
  // Get new text
  const text = getRandomText(sizeCategory);
  
  // Add to recent texts for cache simulation
  recentTexts.push(text);
  if (recentTexts.length > maxRecentTexts) {
    recentTexts.shift(); // Remove oldest
  }
  
  return text;
}

// Make preprocessing request
function makePreprocessingRequest(endpoint, textData, options) {
  const url = `${BASE_URL}/${endpoint}`;
  const payload = {
    text: textData.content,
    options: options
  };
  
  const params = {
    headers: {
      'Content-Type': 'application/json',
    },
    tags: {
      endpoint: endpoint,
      text_size: textData.category,
      text_length: textData.size.toString(),
      has_options: Object.keys(options).length > 0 ? 'true' : 'false'
    }
  };
  
  const response = http.post(url, JSON.stringify(payload), params);
  
  // Record metrics
  httpReqFailed.add(response.status !== 200);
  httpReqDuration.add(response.timings.duration);
  endpointCounter.add(1, { endpoint: endpoint });
  textSizeCounter.add(1, { size: textData.category });
  
  // Validate response
  const success = check(response, {
    'status is 200': (r) => r.status === 200,
    'response has body': (r) => r.body && r.body.length > 0,
    'response is json': (r) => {
      try {
        JSON.parse(r.body);
        return true;
      } catch {
        return false;
      }
    },
    'response time < 5s': (r) => r.timings.duration < 5000,
  });
  
  if (!success) {
    console.log(`Failed request to ${endpoint}: status ${response.status}, body: ${response.body}`);
  }
  
  return response;
}

// Health check request
function makeHealthCheck() {
  const response = http.get(`${BASE_URL}/health`);
  
  check(response, {
    'health check status is 200': (r) => r.status === 200,
    'health check response time < 1s': (r) => r.timings.duration < 1000,
  });
  
  return response;
}

// Main test function
export default function () {
  // Occasional health check (5% of requests)
  if (Math.random() < 0.05) {
    makeHealthCheck();
    return;
  }
  
  // Select text size and endpoint based on configuration
  const selectedSize = weightedRandomSelect(config.textDistribution);
  const selectedEndpoint = weightedRandomSelect(config.endpointDistribution);
  
  // Get text and options
  const textData = getTextForRequest(selectedSize);
  const options = getRandomOptions();
  
  // Make request
  makePreprocessingRequest(selectedEndpoint, textData, options);
  
  // Small sleep to simulate realistic user behavior
  sleep(Math.random() * 0.1); // 0-100ms random sleep
}

// Test scenarios
export const options = {
  scenarios: {

    // // Smoke test
    // smoke_test: {
    //   executor: 'constant-vus',
    //   vus: parseInt(__ENV.SMOKE_VUS || '2'),
    //   duration: __ENV.SMOKE_DURATION || '30s',
    //   tags: { test_type: 'smoke' },
    //   exec: 'smokeTest',
    // },
    
    // // Load test  
    // load_test: {
    //   executor: 'ramping-vus',
    //   startVUs: 0,
    //   stages: [
    //     { duration: '1m', target: parseInt(__ENV.LOAD_VUS || '20') },
    //     { duration: '2m', target: parseInt(__ENV.LOAD_VUS || '20') },
    //     { duration: '1m', target: 0 },
    //   ],
    //   tags: { test_type: 'load' },
    //   exec: 'default',
    // },
    
    // Stress test
    stress_test: {
      executor: 'ramping-vus', 
      startVUs: 0,
      stages: [
        { duration: '5s', target: parseInt(__ENV.STRESS_VUS || '50') },
        { duration: '5s', target: parseInt(__ENV.STRESS_VUS || '50') },
        { duration: '5s', target: parseInt(__ENV.STRESS_PEAK_VUS || '100') },
        { duration: '5s', target: parseInt(__ENV.STRESS_PEAK_VUS || '100') },
        { duration: '5s', target: 0 },
      ],
      tags: { test_type: 'stress' },
      exec: 'default',
    },
  },
  
  // Thresholds
  thresholds: {
    http_req_failed: ['rate<0.05'], // Error rate < 5%
    http_req_duration: [
      'p(95)<2000', // 95% of requests under 2s
      'p(99)<5000', // 99% of requests under 5s
    ],
    'http_req_duration{endpoint:clean}': ['p(95)<1000'],
    'http_req_duration{endpoint:tokenize}': ['p(95)<1500'], 
    'http_req_duration{endpoint:normalize}': ['p(95)<1000'],
  },
};

// Smoke test function
export function smokeTest() {
  // Simple test with one request per endpoint
  const endpoints = ['clean', 'tokenize', 'normalize'];
  const sizes = ['short', 'medium', 'long'];
  
  for (const endpoint of endpoints) {
    for (const size of sizes) {
      const textData = getRandomText(size);
      const options = {};
      makePreprocessingRequest(endpoint, textData, options);
      sleep(0.1);
    }
  }
}

// Setup function
export function setup() {
  console.log('=== Load Test Configuration ===');
  console.log(`Base URL: ${BASE_URL}`);
  console.log(`Text Distribution: ${JSON.stringify(config.textDistribution)}%`);
  console.log(`Endpoint Distribution: ${JSON.stringify(config.endpointDistribution)}%`);
  console.log(`Cache Hit Rate: ${config.cacheHitRate * 100}%`);
  console.log(`Option Variation: ${config.optionVariation * 100}%`);
  console.log('=============================');
  
  // Initial health check
  const healthCheck = http.get(`${BASE_URL}/health`);
  if (healthCheck.status !== 200) {
    throw new Error(`Service health check failed: ${healthCheck.status}`);
  }
  
  console.log(' Service is healthy, starting load test...');
}

// Teardown function  
export function teardown(data) {
  console.log('=== Load Test Complete ===');
  console.log('Check the results above for performance metrics');
}