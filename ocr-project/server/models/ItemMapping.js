const { DataTypes } = require("sequelize");
const sequelize = require("../config/database");

const ItemMapping = sequelize.define("ItemMapping", {
  id: {
    type: DataTypes.INTEGER,
    autoIncrement: true,
    primaryKey: true,
  },
  rawCode: {
    type: DataTypes.STRING,
    allowNull: false,
    index: true,
  },
  canonicalItemCode: {
    type: DataTypes.STRING,
    allowNull: false,
    index: true,
  },
  sourceType: {
    type: DataTypes.STRING, // 'PHYSICAL_DOC', 'ORACLE', 'VENDOR'
    defaultValue: "PHYSICAL_DOC",
  },
  notes: {
    type: DataTypes.STRING,
    allowNull: true,
  },
});

module.exports = ItemMapping;
