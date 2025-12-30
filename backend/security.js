// Security utilities
const bcrypt = require('bcryptjs');
const jwt = require('jsonwebtoken');

const security = {
  // Password hashing
  hashPassword: async (password) => {
    const salt = await bcrypt.genSalt(12);
    return await bcrypt.hash(password, salt);
  },

  // Password verification
  verifyPassword: async (password, hashedPassword) => {
    return await bcrypt.compare(password, hashedPassword);
  },

  // JWT token generation
  generateToken: (payload) => {
    return jwt.sign(payload, process.env.JWT_SECRET || 'fallback_secret', {
      expiresIn: process.env.JWT_EXPIRES_IN || '24h'
    });
  },

  // JWT token verification
  verifyToken: (token) => {
    try {
      return jwt.verify(token, process.env.JWT_SECRET || 'fallback_secret');
    } catch (error) {
      return null;
    }
  },

  // Input sanitization
  sanitizeInput: (input) => {
    if (typeof input !== 'string') return input;
    
    // Remove potentially dangerous characters
    return input
      .trim()
      .replace(/[<>]/g, '')  // Remove HTML tags
      .replace(/\s+/g, ' ')  // Normalize whitespace
      .substring(0, 1000);   // Limit length
  },

  // SQL injection prevention (use parameterized queries)
  validateQueryParams: (params) => {
    const validated = {};
    for (const [key, value] of Object.entries(params)) {
      if (typeof value === 'string') {
        validated[key] = value.substring(0, 1000); // Limit string length
      } else {
        validated[key] = value;
      }
    }
    return validated;
  }
};

module.exports = security;