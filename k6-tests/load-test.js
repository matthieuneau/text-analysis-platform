import { check, sleep } from 'k6';
import http from 'k6/http';

export let options = {
  scenarios: {
    sentiment_analysis: {
      executor: 'ramping-vus',
      exec: 'testSentiment',
      stages: [
        { duration: '20s', target: 5 },
      ],
    },
    summarization: {
      executor: 'ramping-vus',
      exec: 'testSummarization', 
      stages: [
        { duration: '20s', target: 5 },
      ],
    },
    preprocessing: {
        executor: 'ramping-vus',
        exec: 'testPreprocessing',
        stages: [
            {duration: '20s', target: 5},
        ],
    },
    health_checks: {
      executor: 'constant-vus',
      exec: 'testHealth',
      vus: 1,
      duration: '4m',
    },
  },
};

const sentimentPayload = JSON.stringify({
  "text": "I absolutely love this new restaurant! The food was incredible, the service was outstanding, and the atmosphere was perfect."
});

const summaryPayload = JSON.stringify({"text": "Many Puritans had hoped that reforms and reconciliation would be possible when James came to power which would allow them independence, but the Hampton Court Conference of 1604 denied nearly all of the concessions which they had requested—except for an authorized English translation of the Bible. The same year, Richard Bancroft became Archbishop of Canterbury and launched a campaign against Puritanism and the Separatists. He suspended 300 ministers and fired 80 more, which led some of them to found more Separatist churches. Robinson, Clifton, and their followers founded a Brownist church, making a covenant with God to walk in all his ways made known, or to be made known, unto them, according to their best endeavours, whatsoever it should cost them, the Lord assisting them.Archbishop Hutton died in 1606 and Tobias Matthew was appointed as his replacement. He was one of James's chief supporters at the 1604 conference,[8] and he promptly began a campaign to purge the archdiocese of non-conforming influences, including Puritans, Separatists, and those wishing to return to the Catholic faith. Disobedient clergy were replaced, and prominent Separatists were confronted, fined, and imprisoned. He is credited with driving people out of the country who refused to attend Anglican services.[9][10] William Brewster was a former diplomatic assistant to the Netherlands. He was living in the Scrooby manor house while serving as postmaster for the village and bailiff to the Archbishop of York. He had been impressed by Clyfton's services and had begun participating in services led by John Smyth in Gainsborough, Lincolnshire.[11] After a time, he arranged for a congregation to meet privately at the Scrooby manor house. Services were held beginning in 1606 with Clyfton as pastor, John Robinson as teacher, and Brewster as the presiding elder. Shortly after, Smyth and members of the Gainsborough group moved on to Amsterdam.[12] Brewster was fined £20 (about £5,453 today[5]) in absentia for his non-compliance with the church.[13] This followed his September 1607 resignation from the postmaster position,[14] about the time that the congregation had decided to follow the Smyth party to Amsterdam.[3][15] Scrooby member William Bradford of Austerfield kept a journal of the congregation's events which was eventually published as Of Plymouth Plantation.",
"min_length": 50,
"max_length": 70});

const preprocessingPayload = JSON.stringify({
    "text": "Hello World!!! Visit https://example.com for more info.",
    "options": {"remove_urls": true}
});

const headers = { 'Content-Type': 'application/json' };

// Testing the clean endpoint
export function testPreprocessing() {
  let response = http.post('http://gateway:8000/preprocessing/clean', preprocessingPayload, { headers });

    check(response, {
        'preprocessing status is 200': (r) => r.status === 200,
        'preprocessing has result': (r) => r.json().hasOwnProperty('cleaned_text'),
    });
}

export function testSentiment() {
  let response = http.post('http://gateway:8000/sentiment/analyze', sentimentPayload, { headers });
  
  check(response, {
    'sentiment status is 200': (r) => r.status === 200,
    'sentiment has result': (r) => r.json().hasOwnProperty('sentiment'),
  });
  
  sleep(1);
}

export function testSummarization() {
  let response = http.post('http://gateway:8000/summarization/summarize', summaryPayload, { headers });
  
  check(response, {
    'summary status is 200': (r) => r.status === 200,
    'summary has result': (r) => r.json().hasOwnProperty('summary'),
  });
  
  sleep(2);
}

export function testHealth() {
  let response = http.get('http://gateway:8000/health');
  
  check(response, {
    'health status is 200': (r) => r.status === 200,
  });
  
  sleep(10); // Health checks less frequent
}