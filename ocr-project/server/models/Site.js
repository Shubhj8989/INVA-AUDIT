const { DataTypes } = require("sequelize");
const sequelize = require("../config/database");

const Site = sequelize.define("Site", {
  id: {
    type: DataTypes.INTEGER,
    autoIncrement: true,
    primaryKey: true,
  },
  siteCode: {
    type: DataTypes.STRING,
    allowNull: false,
    unique: true,
  },
  siteName: {
    type: DataTypes.STRING,
    allowNull: false,
  },
  location: {
    type: DataTypes.STRING,
    allowNull: true,
  },
  state: {
    type: DataTypes.STRING,
    allowNull: true,
  },
  isActive: {
    type: DataTypes.BOOLEAN,
    defaultValue: true,
  },
});

module.exports = Site;
