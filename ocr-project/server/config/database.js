const { Sequelize } = require("sequelize");
require("dotenv").config();

let sequelize;

try {
  sequelize = new Sequelize(
    process.env.DB_NAME || "ocr_database",
    process.env.DB_USER || "root",
    process.env.DB_PASSWORD || "",
    {
      host: process.env.DB_HOST || "127.0.0.1",
      port: process.env.DB_PORT || 3306,
      dialect: "mysql",
      logging: false,
      pool: {
        max: 10,
        min: 0,
        acquire: 5000,
        idle: 10000,
      },
    }
  );
} catch (e) {
  console.warn("Sequelize init notice:", e.message);
}

module.exports = sequelize;