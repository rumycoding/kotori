# Quick Fix for React-Scripts Issue

## The Problem
You're seeing `react-scripts@0.0.0` which is a broken installation, and the command `'react-scripts' is not recognized`.

## Immediate Solution

Run these commands in the `frontend` directory:

### Option 1: Quick Fix Script
```bash
fix_deps.bat
```

### Option 2: Manual Commands
```bash
# Remove broken installation
npm uninstall react-scripts

# Clean everything
rmdir /s /q node_modules
del package-lock.json
npm cache clean --force

# Install react-scripts specifically
npm install react-scripts@5.0.1 --save --legacy-peer-deps

# Install other dependencies
npm install --legacy-peer-deps

# Start the app
npx react-scripts start
```

### Option 3: Use NPX (Recommended)
```bash
# Just run with npx (no installation needed)
npx react-scripts@5.0.1 start
```

### Option 4: Alternative with Yarn
```bash
# Install yarn if you don't have it
npm install -g yarn

# Install dependencies with yarn
yarn install

# Start with yarn
yarn start
```

## Why This Happens
- npm sometimes installs react-scripts as version 0.0.0 due to dependency conflicts
- The TypeScript version conflict causes incomplete installations
- Using `--legacy-peer-deps` resolves the peer dependency issues

## Verification
After running the fix, verify with:
```bash
npm list react-scripts
```

You should see `react-scripts@5.0.1` instead of `react-scripts@0.0.0`.

## If Still Having Issues
1. Try the enhanced `fix_deps.bat` script
2. Use `npx react-scripts start` instead of `npm start`
3. Switch to yarn as package manager
4. Check that Node.js version is 16+ with `node --version`