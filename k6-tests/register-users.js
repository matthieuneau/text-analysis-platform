import { check, sleep } from 'k6';
import http from 'k6/http';
import { Counter, Rate } from 'k6/metrics';

// Custom metrics
const registrationCounter = new Counter('user_registrations_total');
const registrationFailureRate = new Rate('user_registration_failures');

export const options = {
  stages: [
    { duration: '30s', target: 10 }, // Ramp up to 10 concurrent users
    { duration: '2m', target: 10 },  // Stay at 10 users for 2 minutes
    { duration: '30s', target: 0 },  // Ramp down
  ],
  thresholds: {
    http_req_duration: ['p(95)<2000'], // 95% of requests should be below 2s
    http_req_failed: ['rate<0.1'],     // Less than 10% of requests should fail
    user_registration_failures: ['rate<0.05'], // Less than 5% registration failures
  },
};

// Generate unique user data
function generateUserData(userId) {
  const timestamp = Date.now();
  const randomSuffix = Math.floor(Math.random() * 10000);
  
  return {
    username: `testuser${userId}_${randomSuffix}`,
    email: `testuser${userId}_${randomSuffix}@example.com`,
    password: `SecurePass123!${userId}` // Meets min 8 chars requirement
  };
}

export default function () {
  // Generate unique user ID for this iteration
  const userId = __VU * 1000 + __ITER;
  const userData = generateUserData(userId);
  
  const params = {
    headers: {
      'Content-Type': 'application/json',
      'User-Agent': 'k6-load-test/1.0',
    },
    timeout: '30s',
  };

  // Register user
  const registerResponse = http.post(
    'http://gateway:8080/auth/register', // Adjust URL based on your gateway config
    JSON.stringify(userData),
    params
  );

  // Check registration response
  const registrationSuccess = check(registerResponse, {
    'registration status is 200': (r) => r.status === 200,
    'registration response has user data': (r) => {
      try {
        const body = JSON.parse(r.body);
        return body.username && body.email && body.id;
      } catch (e) {
        return false;
      }
    },
    'registration response time < 5s': (r) => r.timings.duration < 5000,
  });

  // Update custom metrics
  registrationCounter.add(1);
  if (!registrationSuccess) {
    registrationFailureRate.add(1);
    console.error(`Registration failed for user ${userData.username}: ${registerResponse.status} - ${registerResponse.body}`);
  } else {
    console.log(`Successfully registered user: ${userData.username}`);
  }

  // Small delay between requests to avoid overwhelming the server
  sleep(1);
}

// Setup function - runs once before the test starts
export function setup() {
  console.log('Starting k6 user registration test...');
  console.log('Target: 100 user registrations');
  
  // Test connectivity to the auth service
  const healthCheck = http.get('http://gateway:8080/health', {
    timeout: '10s',
  });
  
  if (healthCheck.status !== 200) {
    console.error('Health check failed - service may not be ready');
    console.error(`Health check response: ${healthCheck.status} - ${healthCheck.body}`);
  } else {
    console.log('Service health check passed');
  }
}

// Teardown function - runs once after the test completes
export function teardown() {
  console.log('k6 user registration test completed');
}