<?php
include "config.php";
include "functions.php";

// Only allow POST requests
if ($_SERVER['REQUEST_METHOD'] !== 'POST') exit;

// Read incoming update
$update = json_decode(file_get_contents("php://input"), true);

// File to store temporary user state
$stateFile = "user_state.json";
$states = file_exists($stateFile) ? json_decode(file_get_contents($stateFile), true) : [];

// Get user ID from message or callback
$user_id = $update["message"]["from"]["id"] 
    ?? $update["callback_query"]["from"]["id"] 
    ?? null;

// Restrict access to only your Telegram ID
if ($user_id != $allowedUser) exit;

// ------------------ CALLBACK HANDLING ------------------
if (isset($update["callback_query"])) {

    $callback = $update["callback_query"];
    $data = $callback["data"];
    $chat_id = $callback["message"]["chat"]["id"];
    $callback_id = $callback["id"];

    answerCallback($callback_id);

    // ------------------ CASE 2: User selected title ------------------
    if (isset($states[$chat_id]["link"])) {
        $link = $states[$chat_id]["link"];   // Link user sent
        $title = $data;                      // Selected title button

        // Update the link in links.txt
        updateLinkInFile("links.txt", $title, $link);

        // Push to GitHub
        pushFileToGitHub("links.txt");

        // Clear user state
        unset($states[$chat_id]);
        file_put_contents($stateFile, json_encode($states));

        sendMessage($chat_id, "✅ Updated successfully & synced to GitHub!");
        exit;
    }
}

// ------------------ MESSAGE HANDLING ------------------
if (isset($update["message"])) {

    $chat_id = $update["message"]["chat"]["id"];
    $text = $update["message"]["text"] ?? "";
    $video = $update["message"]["video"] ?? null;

    // /start command
    if ($text === "/start") {
        sendMessage($chat_id, "Send a video (for Case 1) or a direct link (for Case 2):");
        exit;
    }

    // ------------------ CASE 1: Video Update ------------------
    if ($video) {
        $fileName = $video["file_name"] ?? "";
        $download_link = generateDownloadLink($video); // Your function to generate link

        // Titles to match
        $titles = ["Master Chef","Wheel of fortune","50","Laughter Chef"];

        foreach ($titles as $title) {
            if (titleMatchesFileName($title, $fileName)) {
                updateLinkInFile("links.txt", $title, $download_link);
                pushFileToGitHub("links.txt");
                sendMessage($chat_id, "✅ Video link for '$title' updated successfully!");
                exit;
            }
        }

        sendMessage($chat_id, "⚠ No matching title found for this video.");
        exit;
    }

    // ------------------ CASE 2: Direct link ------------------
    if (filter_var($text, FILTER_VALIDATE_URL)) {

        // Save the link temporarily in user_state.json
        $states[$chat_id]["link"] = $text;
        file_put_contents($stateFile, json_encode($states));

        // Send inline keyboard to select title
        $keyboard = [
            "inline_keyboard" => [
                [["text"=>"Sky","callback_data"=>"Sky"],
                 ["text"=>"Willow","callback_data"=>"Willow"]],
                [["text"=>"Prime1","callback_data"=>"Prime1"],
                 ["text"=>"Prime2","callback_data"=>"Prime2"]]
            ]
        ];

        sendMessage($chat_id, "Select the title to update:", $keyboard);
        exit;
    }

    sendMessage($chat_id, "⚠ Please send a valid video (for Case 1) or a direct link (for Case 2).");
}

// ------------------ HELPER FUNCTIONS ------------------

// Check if video file name matches title words
function titleMatchesFileName($title, $fileName) {
    $titleWords = preg_split("/[\s]+/", strtolower($title));
    $fileLower = strtolower($fileName);

    foreach ($titleWords as $word) {
        if (!preg_match("/\b".preg_quote($word)."\b/", $fileLower)) {
            return false;
        }
    }

    // Special rule for "50": check if "The" appears just before "50"
    if ($title === "50") {
        if (!preg_match("/\bthe[\._\s]*50\b/i", $fileLower)) {
            return false;
        }
    }

    return true;
}

?>
