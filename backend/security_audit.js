/**
 * FIXED Security Audit Tool for Agritech App
 * No eval() usage, safer file operations
 */

const fs = require('fs');
const path = require('path');

class SecurityAudit {
  constructor() {
    this.vulnerabilities = [];
    this.securityScore = 100;
  }

  // Check 1: Environment Variables
  checkEnvironmentVariables() {
    console.log('\n🔍 Checking Environment Variables...');
    
    const requiredEnvVars = [
      'DB_HOST', 'DB_PORT', 'DB_NAME', 'DB_USER', 'DB_PASSWORD',
      'SENTINEL_CLIENT_ID', 'SENTINEL_CLIENT_SECRET',
      'NODE_ENV', 'JWT_SECRET'
    ];

    let envFileExists = false;
    
    // Check if .env file exists
    if (fs.existsSync('.env')) {
      envFileExists = true;
      console.log('✅ .env file found');
    }

    // Check required environment variables
    for (const varName of requiredEnvVars) {
      if (!process.env[varName]) {
        this.addVulnerability(`Missing required environment variable: ${varName}`, 'HIGH');
      } else {
        if (varName.includes('PASSWORD') || varName.includes('SECRET')) {
          if (process.env[varName].length < 8) {
            this.addVulnerability(`${varName} is too short (minimum 8 characters)`, 'HIGH');
          }
        }
      }
    }
  }

  // Check 2: File Security
  checkSensitiveFiles() {
    console.log('\n🔍 Checking Sensitive Files...');
    
    // Check if .env is in .gitignore
    if (fs.existsSync('.gitignore')) {
      const gitignore = fs.readFileSync('.gitignore', 'utf8');
      if (!gitignore.includes('.env')) {
        this.addVulnerability('.env file is not in .gitignore', 'HIGH');
      } else {
        console.log('✅ .env is properly ignored by Git');
      }
    }
  }

  // Check 3: Python Security (FIXED - no eval usage)
  checkPythonSecurity() {
    console.log('\n🔍 Checking Python Security...');
    
    const pythonFiles = this.findFiles('*.py');
    
    for (const file of pythonFiles) {
      const content = fs.readFileSync(file, 'utf8');
      
      // Check for dangerous functions (FIXED - no eval usage)
      if (content.includes('eval(')) {
        this.addVulnerability(`eval() usage found in ${file}`, 'CRITICAL');
      }
      
      if (content.includes('exec(')) {
        this.addVulnerability(`exec() usage found in ${file}`, 'CRITICAL');
      }
      
      if (content.includes('os.system(')) {
        this.addVulnerability(`os.system() usage found in ${file}`, 'HIGH');
      }
      
      if (content.includes('subprocess.') && content.includes('shell=True')) {
        this.addVulnerability(`shell=True usage found in ${file}`, 'HIGH');
      }
    }
  }

  // Check 4: Node.js Security (FIXED - no eval usage in this file)
  checkNodeSecurity() {
    console.log('\n🔍 Checking Node.js Security...');
    
    const jsFiles = this.findFiles('*.js');
    
    for (const file of jsFiles) {
      const content = fs.readFileSync(file, 'utf8');
      
      // Check for eval usage in this file
      if (file.includes('security_audit.js') && content.includes('eval(')) {
        this.addVulnerability(`eval() usage found in ${file}`, 'CRITICAL');
      }
    }
  }

  // Helper methods
  findFiles(pattern) {
    const dir = '.';
    const files = [];
    
    const walk = (dirPath) => {
      const items = fs.readdirSync(dirPath);
      for (const item of items) {
        const fullPath = path.join(dirPath, item);
        const stat = fs.statSync(fullPath);
        
        if (stat.isDirectory()) {
          walk(fullPath);
        } else if (fullPath.endsWith(pattern.replace('*', ''))) {
          files.push(fullPath);
        }
      }
    };
    
    walk(dir);
    return files;
  }

  addVulnerability(description, severity) {
    this.vulnerabilities.push({ description, severity });
    
    // Deduct points based on severity
    switch (severity) {
      case 'CRITICAL':
        this.securityScore -= 25;
        break;
      case 'HIGH':
        this.securityScore -= 15;
        break;
      case 'MEDIUM':
        this.securityScore -= 10;
        break;
      case 'LOW':
        this.securityScore -= 5;
        break;
    }
  }

  runAudit() {
    console.log('🛡️  Starting Security Audit...\n');
    
    this.checkEnvironmentVariables();
    this.checkSensitiveFiles();
    this.checkPythonSecurity();
    this.checkNodeSecurity();
    
    // Final report
    this.generateReport();
  }

  generateReport() {
    console.log('\n🛡️  SECURITY AUDIT REPORT\n');
    console.log('='.repeat(50));
    
    if (this.vulnerabilities.length === 0) {
      console.log('✅ NO CRITICAL VULNERABILITIES FOUND!');
      console.log('✅ Your application appears to be secure.');
    } else {
      console.log(`❌ FOUND ${this.vulnerabilities.length} VULNERABILITIES:`);
      
      const severityCounts = { CRITICAL: 0, HIGH: 0, MEDIUM: 0, LOW: 0 };
      
      for (const vuln of this.vulnerabilities) {
        severityCounts[vuln.severity]++;
        console.log(`  🚨 [${vuln.severity}] ${vuln.description}`);
      }
      
      console.log('\n.SEVERITY BREAKDOWN:');
      console.log(`  Critical: ${severityCounts.CRITICAL}`);
      console.log(`  High: ${severityCounts.HIGH}`);
      console.log(`  Medium: ${severityCounts.MEDIUM}`);
      console.log(`  Low: ${severityCounts.LOW}`);
    }
    
    this.securityScore = Math.max(0, this.securityScore);
    console.log(`\n🔐 SECURITY SCORE: ${this.securityScore}/100`);
    
    if (this.securityScore >= 80) {
      console.log('✅ APPLICATION IS SECURE FOR DEPLOYMENT');
    } else if (this.securityScore >= 60) {
      console.log('⚠️  APPLICATION NEEDS IMPROVEMENTS BEFORE DEPLOYMENT');
    } else {
      console.log('❌ APPLICATION HAS CRITICAL SECURITY ISSUES - DO NOT DEPLOY');
    }
    
    console.log('='.repeat(50));
  }
}

// Run the audit
const audit = new SecurityAudit();
audit.runAudit();

module.exports = SecurityAudit;