<?php
include "config.php";
include "functions.php";

if ($_SERVER['REQUEST_METHOD'] !== 'POST') exit;

$update = json_decode(file_get_contents("php://input"), true);

$user_id = $update["message"]["from"]["id"]
    ?? $update["callback_query"]["from"]["id"]
    ?? null;

if ($user_id != $allowedUser) exit;

/* ================= CALLBACK ================= */

if (isset($update["callback_query"])) {

    $callback = $update["callback_query"];
    $chat_id = $callback["message"]["chat"]["id"];
    $title = $callback["data"];
    $callback_id = $callback["id"];

    answerCallback($callback_id);

    $link = getTempLink($chat_id);
    if (!$link) {
        sendMessage($chat_id, "Send link again.");
        exit;
    }

    updateLinkInFile("links.txt", $title, $link);
    pushFileToGitHub("links.txt");

    clearTempLink($chat_id);

    sendMessage($chat_id, "✅ Updated & synced to GitHub.");
    exit;
}

/* ================= MESSAGE ================= */

if (isset($update["message"])) {

    $chat_id = $update["message"]["chat"]["id"];
    $text = $update["message"]["text"] ?? "";
    $video = $update["message"]["video"] ?? null;

    if ($text === "/start") {
        sendMessage($chat_id, "Send video (Case 1) or direct link (Case 2).");
        exit;
    }

    /* -------- CASE 1 : VIDEO -------- */

    if ($video) {

        $fileName = strtolower($video["file_name"] ?? "");

        $titles = [
            "Master Chef",
            "Wheel of fortune",
            "50",
            "Laughter Chef"
        ];

        foreach ($titles as $title) {
            if (titleMatches($title, $fileName)) {

                $downloadLink = generateTelegramDownloadLink($video["file_id"]);

                if (!$downloadLink) {
                    sendMessage($chat_id, "Failed to generate download link.");
                    exit;
                }
                
                updateLinkInFile("links.txt", $title, $downloadLink);
                
                if (pushFileToGitHub("links.txt")) {
                    sendMessage($chat_id, "✅ $title updated & synced.");
                } else {
                    sendMessage($chat_id, "Updated locally but GitHub push failed.");
                }

                exit;
            }
        }

        sendMessage($chat_id, "No matching title found.");
        exit;
    }

    /* -------- CASE 2 : DIRECT LINK -------- */

    if (filter_var($text, FILTER_VALIDATE_URL)) {

        saveTempLink($chat_id, $text);

        $keyboard = [
            "inline_keyboard" => [
                [
                    ["text"=>"Sky","callback_data"=>"Sky"],
                    ["text"=>"Willow","callback_data"=>"Willow"]
                ],
                [
                    ["text"=>"Prime1","callback_data"=>"Prime1"],
                    ["text"=>"Prime2","callback_data"=>"Prime2"]
                ]
            ]
        ];

        sendMessage($chat_id, "Select title:", $keyboard);
        exit;
    }

    sendMessage($chat_id, "Invalid input.");
}
?>
