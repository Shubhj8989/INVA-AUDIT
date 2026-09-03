const { DataTypes } = require("sequelize");
const sequelize = require("../config/database");

const Document = sequelize.define(
  "Document",
  {
    id: {
      type: DataTypes.BIGINT,
      autoIncrement: true,
      primaryKey: true,
    },

    fileName: {
      type: DataTypes.STRING,
      allowNull: false,
    },

    filePath: {
      type: DataTypes.STRING(1000),
      allowNull: false,
    },

    extractedText: {
      type: DataTypes.TEXT("long"),
      allowNull: true,
    },

    status: {
      type: DataTypes.ENUM(
        "PENDING",
        "PROCESSING",
        "COMPLETED",
        "FAILED"
      ),
      defaultValue: "PENDING",
    },
  },
  {
    tableName: "documents",
    timestamps: true,
  }
);

module.exports = Document;