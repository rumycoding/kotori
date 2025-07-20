#!/usr/bin/env node

/**
 * Frontend startup script for Kotori Bot UI
 * 
 * This script helps with the development setup and provides
 * helpful information about the frontend development environment.
 */

const { spawn } = require('child_process');
const fs = require('fs');
const path = require('path');

function checkNodeVersion() {
  const version = process.version;
  const majorVersion = parseInt(version.slice(1).split('.')[0]);
  
  if (majorVersion < 16) {
    console.log('❌ Node.js version 16 or higher is required');
    console.log(`   Current version: ${version}`);
    console.log('   Please upgrade Node.js: https://nodejs.org/');
    process.exit(1);
  }
  
  console.log(`✅ Node.js version: ${version}`);
}

function checkPackageJson() {
  const packageJsonPath = path.join(__dirname, 'package.json');
  
  if (!fs.existsSync(packageJsonPath)) {
    console.log('❌ package.json not found');
    console.log('   Make sure you are in the frontend directory');
    process.exit(1);
  }
  
  console.log('✅ package.json found');
}

function checkDependencies() {
  const nodeModulesPath = path.join(__dirname, 'node_modules');
  
  if (!fs.existsSync(nodeModulesPath)) {
    console.log('⚠️  Dependencies not installed');
    console.log('   Installing dependencies...');
    
    return new Promise((resolve, reject) => {
      const npmInstall = spawn('npm', ['install'], {
        stdio: 'inherit',
        shell: true
      });
      
      npmInstall.on('close', (code) => {
        if (code === 0) {
          console.log('✅ Dependencies installed successfully');
          resolve();
        } else {
          console.log('❌ Failed to install dependencies');
          reject(new Error('npm install failed'));
        }
      });
    });
  } else {
    console.log('✅ Dependencies already installed');
    return Promise.resolve();
  }
}

function checkBackendConnection() {
  console.log('🔍 Checking backend connection...');
  
  return fetch('http://localhost:8000/api/health')
    .then(response => {
      if (response.ok) {
        console.log('✅ Backend is running and accessible');
        return true;
      } else {
        console.log('⚠️  Backend is running but returned error status');
        return false;
      }
    })
    .catch(error => {
      console.log('⚠️  Backend not accessible at http://localhost:8000');
      console.log('   Make sure the backend is running with: python run_backend.py');
      return false;
    });
}

function startDevelopmentServer() {
  console.log('\n🚀 Starting React development server...');
  console.log('📊 Frontend will be available at: http://localhost:3000');
  console.log('🔄 Hot reload is enabled for development');
  console.log('\n' + '='.repeat(50));
  console.log('💡 Development Tips:');
  console.log('   - Make sure the backend is running on port 8000');
  console.log('   - The app will automatically reload when you make changes');
  console.log('   - Press Ctrl+C to stop the development server');
  console.log('   - Check browser console for any errors');
  console.log('='.repeat(50) + '\n');
  
  const reactStart = spawn('npm', ['start'], {
    stdio: 'inherit',
    shell: true
  });
  
  reactStart.on('close', (code) => {
    if (code !== 0) {
      console.log(`\n❌ Development server exited with code ${code}`);
    } else {
      console.log('\n🛑 Development server stopped');
    }
  });
  
  // Handle Ctrl+C gracefully
  process.on('SIGINT', () => {
    console.log('\n🛑 Stopping development server...');
    reactStart.kill('SIGINT');
  });
}

async function main() {
  console.log('🎨 Kotori Bot Frontend - Development Setup');
  console.log('='.repeat(50));
  
  try {
    // Check environment
    checkNodeVersion();
    checkPackageJson();
    
    // Install dependencies if needed
    await checkDependencies();
    
    // Check backend (non-blocking)
    if (typeof fetch !== 'undefined') {
      await checkBackendConnection();
    } else {
      console.log('⚠️  Cannot check backend connection (fetch not available)');
      console.log('   Make sure backend is running: python run_backend.py');
    }
    
    console.log('\n✅ All checks passed! Starting development server...\n');
    
    // Start the development server
    startDevelopmentServer();
    
  } catch (error) {
    console.log(`\n❌ Setup failed: ${error.message}`);
    console.log('\nPlease fix the issues above and try again.');
    process.exit(1);
  }
}

// For older Node.js versions without fetch
if (typeof fetch === 'undefined') {
  global.fetch = require('node-fetch');
}

if (require.main === module) {
  main();
}