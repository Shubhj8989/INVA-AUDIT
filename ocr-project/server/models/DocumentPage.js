const { DataTypes } = require("sequelize");
const sequelize = require("../config/database");

const DocumentPage = sequelize.define("DocumentPage", {
  id: {
    type: DataTypes.INTEGER,
    autoIncrement: true,
    primaryKey: true,
  },
  documentId: {
    type: DataTypes.INTEGER,
    allowNull: false,
  },
  pageNumber: {
    type: DataTypes.INTEGER,
    defaultValue: 1,
  },
  totalPages: {
    type: DataTypes.INTEGER,
    defaultValue: 1,
  },
  imagePath: {
    type: DataTypes.STRING,
    allowNull: true,
  },
  rawOcrJson: {
    type: DataTypes.TEXT, // Raw OCR bounding boxes and words
    allowNull: true,
  },
});

module.exports = DocumentPage;
