const { DataTypes } = require("sequelize");
const sequelize = require("../config/database");

const ItemMaster = sequelize.define("ItemMaster", {
  id: {
    type: DataTypes.INTEGER,
    autoIncrement: true,
    primaryKey: true,
  },
  itemCode: {
    type: DataTypes.STRING,
    allowNull: false,
    unique: true,
    index: true,
  },
  itemDescription: {
    type: DataTypes.TEXT,
    allowNull: true,
  },
  category: {
    type: DataTypes.STRING,
    allowNull: true,
  },
  defaultUOM: {
    type: DataTypes.STRING,
    defaultValue: "PCS",
  },
  hsnCode: {
    type: DataTypes.STRING,
    allowNull: true,
  },
});

module.exports = ItemMaster;
