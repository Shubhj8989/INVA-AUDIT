const express = require("express");
const multer = require("multer");
const path = require("path");
const fs = require("fs");

const axios = require("axios");
const FormData = require("form-data");

const Document = require("../models/document");

const router = express.Router();


// Configure uploaded image storage
const storage = multer.diskStorage({
  destination: (req, file, cb) => {
    cb(null, "uploads/");
  },

  filename: (req, file, cb) => {
    const uniqueName =
      Date.now() +
      "-" +
      Math.round(Math.random() * 1e9);

    cb(
      null,
      uniqueName +
      path.extname(file.originalname)
    );
  },
});

const upload = multer({ storage });


// =====================================
// UPLOAD IMAGE + OCR
// =====================================

router.post(
  "/upload",
  upload.single("image"),
  async (req, res) => {

    try {

      if (!req.file) {
        return res.status(400).json({
          message: "Please upload an image",
        });
      }


      // Save document information
      const document = await Document.create({
        fileName: req.file.originalname,
        filePath: req.file.path,
        status: "PROCESSING",
      });


      console.log(
        "Sending image to Python OCR service..."
      );


      // Create form data
      const formData = new FormData();

      formData.append(
        "image",
        fs.createReadStream(req.file.path)
      );


      // Send image to Python
      const response = await axios.post(
        "http://127.0.0.1:5001/process",
        formData,
        {
          headers: formData.getHeaders(),
        }
      );


      // Python OCR result
      const {
        text,
        words,
        layout,
      } = response.data;


      console.log(
        "OCR completed successfully"
      );

      console.log(
        "Extracted words:",
        words.length
      );


      // Save OCR result
      await document.update({
        extractedText: text,

        status: "COMPLETED",
      });


      // Send result to React
      res.json({

        message:
          "OCR completed successfully",

        document: {

          id: document.id,

          fileName:
            document.fileName,

          extractedText:
            text,

          words:
            words,
            layout: layout,

        },

      });


    } catch (error) {

      console.error(
        "OCR Error:",
        error.message
      );


      res.status(500).json({

        message:
          "OCR failed",

        error:
          error.message,

      });

    }

  }
);


// =====================================
// GET ALL DOCUMENTS
// =====================================

router.get(
  "/documents",
  async (req, res) => {

    try {

      const documents =
        await Document.findAll({

          order: [
            ["createdAt", "DESC"]
          ],

        });


      res.json(
        documents
      );


    } catch (error) {

      console.error(
        error
      );


      res.status(500).json({

        message:
          "Error fetching documents",

      });

    }

  }
);


module.exports = router;