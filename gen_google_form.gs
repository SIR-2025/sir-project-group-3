function createFormFromCSV() {
  const START_ROW = 3; // first data row (1-based)
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sheet = ss.getActiveSheet();
  const data = sheet.getDataRange().getValues();

  // Header row
  const headers = data[0];
  const COL_USER = headers.indexOf("user_text");
  const COL_NAO = headers.indexOf("nao_text");

  if (COL_USER === -1 || COL_NAO === -1) {
    throw new Error("Could not find 'user_text' and/or 'nao_text' headers.");
  }

  // Create the form
  const form = FormApp.create("SIR - Nao Chat History Questionnaire");

  form.setDescription(
    "Welcome to the evaluation questionnaire.\n\n" +
    "Each section contains a chat round between the USER and NAO.\n" +
    "Please review the content and answer the evaluation questions, starting on the next page." +
    "\n\n\nBefore beginning the interaction, the user gets an introduction to the story:" +
    "\n\nA long, long time ago, on a distant continent, stood an ancient castle. An old legend circulated " +
    "throughout the land, telling of endless gold and riches hidden within the castle. Countless " +
    "adventurers tried to enter the castle, but all have failed. You enter a crowded frontier tavern, " +
    "alive with the noise of travellers swapping stories and sheltering from the cold night. Every " +
    "table is taken except one, where a lone adventurer (NAO) sits quietly observing the room. You are a weary " +
    "traveller yourself, carrying your own tales from the road. Your only aim for now is to share the " +
    "table and strike up natural conversation; how things unfold will depend on the rapport you build.\n\n\n" +
    "The first round is completely scripted:\n\n" +
    "USER:\nHey there! Mind if I share a table with you? this place is packed!\n\n" +
    "NAO:\nOf course, friend! The more, the merrier, they say. It does seem like everyone in town decided to " +
    "gather here tonight, doesn't it? You look a bit weary—long travels, I take it? Where have you come from?" +
    "\n\n\nPress 'Next' to get to the next round..."
  );

  // Loop rows starting at START_ROW
  for (let i = START_ROW - 1; i < data.length; i++) {
    const row = data[i];
    const userText = row[COL_USER];
    const naoText = row[COL_NAO];

    if (!userText && !naoText) continue;

    const roundNumber = i + 1;  // sheet row number
    const displayRound = roundNumber - 1; // <-- your change

    // SECTION HEADER
    const section = form.addPageBreakItem();
    section.setTitle(`Chat History - Round ${displayRound}`);

    const description =
      "USER:\n" +
      (userText || "") + "\n\n" +
      "NAO:\n" +
      (naoText || "");

    section.setHelpText(description);

    // ---- QUESTIONS ----

    // Q1 Likert scale 1–4
    const q1 = form.addScaleItem();
    q1.setTitle(
      "This question is about NAO's response.\n\n" +
      "How relevant was NAO's response to the current user input?"
    )
      .setBounds(1, 4)
      .setLabels("Completely Irrelevant", "Completely Relevant");

    // Q2 Likert scale 1–4
    const q2 = form.addScaleItem();
    q2.setTitle(
      "This question is about NAO's response.\n\n" +
      "How relevant was NAO's response in relation to the earlier chat history (including the current round)?"
    )
      .setBounds(1, 4)
      .setLabels("Completely Irrelevant", "Completely Relevant");

    // Q3 Checkbox multi-select
    const q3 = form.addCheckboxItem();
    q3.setTitle(
      "This question is about the USER's input.\n\n" +
      "Score the friendliness of the USER (refferred to as the traveller), by ticking the appropriate boxes. " +
      "You can tick any number of boxes. Ticking no boxes indicates that the USER (traveller) has a neutral tone."
    );

    const checkboxOptions = [
      { code: "A", text: "The traveller starts with a friendly or respectful greeting" },
      { code: "B", text: "The traveller talking in a friendly or kind tone" },
      { code: "C", text: "The traveller talking in a polite tone" },
      { code: "D", text: "The traveller talking in a cold or indifferent tone" },
      { code: "E", text: "The traveller shows appreciation or thanks during the conversation" },
      { code: "F", text: "The traveller willingly shares personal stories or experiences or tastes" },
      { code: "G", text: "The traveller engages by asking questions about your stories or preferences" },
      { code: "H", text: "The traveller expresses sympathy or understanding of your experiences or stories" },
      { code: "I", text: "The traveller demonstrates impatience, tries to rush the conversation, or demands information" },
      { code: "J", text: "The traveller makes dismissive, rude, or disrespectful remarks" }
    ];

    q3.setChoices(
      checkboxOptions.map(opt =>
        q3.createChoice(`${opt.code}: ${opt.text}`)
      )
    );
  }

  Logger.log("Form created: " + form.getEditUrl());
}
