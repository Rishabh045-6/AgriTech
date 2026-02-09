#!/usr/bin/env node
// Test the /api/generate-recommendations endpoint

const http = require('http');

const data = JSON.stringify({
    plotId: 'test1',
    farmerId: 'farmer1',
    plotFeatures: {
        disease_detection: { risk_level: 'low' },
        water_stress: { stress: 'moderate' },
        pest_risk: { risk_level: 'low' },
        stage_classifier: { stage: 'vegetative' },
        current_crop: 'wheat'
    }
});

const options = {
    hostname: 'localhost',
    port: 3001,
    path: '/api/generate-recommendations',
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
        'Content-Length': data.length
    }
};

const req = http.request(options, (res) => {
    let responseData = '';

    res.on('data', (chunk) => {
        responseData += chunk;
    });

    res.on('end', () => {
        console.log('Status:', res.statusCode);
        console.log('Response:');
        try {
            const parsed = JSON.parse(responseData);
            console.log(JSON.stringify(parsed, null, 2));
        } catch (e) {
            console.log(responseData);
        }
    });
});

req.on('error', (error) => {
    console.error('Request error:', error.message);
});

req.write(data);
req.end();
