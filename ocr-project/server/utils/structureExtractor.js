function cleanText(text) {
  return text
    .replace(/\r/g, "")
    .replace(/[ \t]+/g, " ")
    .trim();
}


function extractDocumentStructure(text) {

  const lines = text
    .split("\n")
    .map((line) => cleanText(line))
    .filter((line) => line.length > 0);


  console.log("LINES CREATED:", lines.length);

  console.log(
    "FIRST 10 LINES:",
    lines.slice(0, 10)
  );


  const fullText = lines.join("\n");


  const structuredData = {

    document: {
      company: null,
      title: null,
      documentNumber: null,
    },

    customer: {
      customerCode: null,
      customerName: null,
      address: null,
      mobileNumber: null,
    },

    pickingDetails: {
      pickSlipNo: null,
      toLocation: null,
      pickSlipDate: null,
      reportRunDate: null,
      subInventory: null,
      productCategory: null,
      orderType: null,
      weightInKg: null,
    },

    products: [],

    rawLines: lines,
  };


  // Company
  const companyLine = lines.find((line) =>
    line.toLowerCase().includes("panasonic")
  );

  if (companyLine) {
    structuredData.document.company =
      "Panasonic";
  }


  // Document Title
  const titleLine = lines.find((line) =>
    line.toLowerCase().includes("picking instruction")
  );

  if (titleLine) {
    structuredData.document.title =
      "Picking Instruction";
  }


  // Mobile Number
  const mobileMatch = fullText.match(
    /\b\d{10}\b/
  );

  if (mobileMatch) {
    structuredData.customer.mobileNumber =
      mobileMatch[0];
  }


  // Address
  const addressKeywords = [
    "bhavan",
    "complex",
    "road",
    "pune",
    "nashik",
    "maharashtra",
  ];

  const addressLines = lines.filter((line) => {

    const lowerLine =
      line.toLowerCase();

    return addressKeywords.some((keyword) =>
      lowerLine.includes(keyword)
    );

  });

  if (addressLines.length > 0) {

    structuredData.customer.address =
      addressLines.join(", ");

  }


  // Pick Slip Number
  const pickSlipMatch = fullText.match(
    /(?:pick\s*slip|picking).*?(\d{5,})/i
  );

  if (pickSlipMatch) {

    structuredData.pickingDetails.pickSlipNo =
      pickSlipMatch[1];

  }


  // Date
  const dateMatch = fullText.match(
    /\b\d{1,2}[-\/][A-Za-z]{3}[-\/]\d{2,4}\b/i
  );

  if (dateMatch) {

    structuredData.pickingDetails.pickSlipDate =
      dateMatch[0];

  }


  return structuredData;

}


module.exports = {
  extractDocumentStructure,
};