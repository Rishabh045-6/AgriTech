module.exports = {
  database: {
    host: process.env.DB_HOST,
    port: process.env.DB_PORT,
    database: process.env.DB_NAME,
    user: process.env.DB_USER,
    password: process.env.DB_PASSWORD,
  },
  server: {
    port: process.env.PORT || 3001,
    environment: process.env.NODE_ENV || 'development',
  },
  sentinel: {
    clients: [
      {
        id: process.env.SENTINEL_CLIENT_1_ID,
        secret: process.env.SENTINEL_CLIENT_1_SECRET
      },
      {
        id: process.env.SENTINEL_CLIENT_2_ID,
        secret: process.env.SENTINEL_CLIENT_2_SECRET
      }
    ].filter(client => client.id && client.secret)
  },
  paths: {
    models: process.env.MODELS_PATH || './models',
    scalers: process.env.SCALERS_PATH || './scalers',
    data: process.env.DATA_PATH || './data'
  }
};