<?php
// Telegram API helper
function sendMessage($chat_id, $text, $keyboard = null) {
    global $apiURL;

    $data = [
        "chat_id" => $chat_id,
        "text" => $text
    ];

    if ($keyboard !== null) {
        $data["reply_markup"] = json_encode($keyboard);
    }

    file_get_contents($apiURL . "sendMessage?" . http_build_query($data));
}

function answerCallback($callback_id) {
    global $apiURL;
    file_get_contents($apiURL . "answerCallbackQuery?callback_query_id=" . $callback_id);
}

// Update a link in links.txt based on the title
function updateLinkInFile($file, $title, $newLink) {
    if (!file_exists($file)) {
        file_put_contents($file, "");
    }

    $lines = file($file, FILE_IGNORE_NEW_LINES);
    $found = false;

    for ($i = 0; $i < count($lines); $i++) {
        if (trim($lines[$i]) === $title) {
            $lines[$i + 1] = $newLink; // Replace the next line
            $found = true;
            break;
        }
    }

    // If title not found, append at end
    if (!$found) {
        $lines[] = $title;
        $lines[] = $newLink;
    }

    file_put_contents($file, implode(PHP_EOL, $lines));
}

// Push file to GitHub
function pushFileToGitHub($filePath, $branch = 'main') {
    $githubToken = getenv('GITHUB_TOKEN');
    $repo = getenv('GITHUB_REPO'); // format: username/repo

    $fileName = basename($filePath);
    $content = file_get_contents($filePath);
    $base64Content = base64_encode($content);

    // Get current file SHA
    $url = "https://api.github.com/repos/$repo/contents/$fileName?ref=$branch";

    $ch = curl_init($url);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_USERAGENT, "TelegramBot");
    curl_setopt($ch, CURLOPT_HTTPHEADER, [
        "Authorization: token $githubToken"
    ]);
    $response = curl_exec($ch);
    curl_close($ch);

    $json = json_decode($response, true);
    $sha = $json['sha'] ?? null;

    if (!$sha) {
        error_log("GitHub SHA fetch failed for $fileName");
        return false;
    }

    // Push updated content
    $data = [
        "message" => "Updated $fileName via Telegram bot",
        "content" => $base64Content,
        "sha" => $sha,
        "branch" => $branch
    ];

    $ch = curl_init("https://api.github.com/repos/$repo/contents/$fileName");
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_USERAGENT, "TelegramBot");
    curl_setopt($ch, CURLOPT_HTTPHEADER, [
        "Authorization: token $githubToken",
        "Content-Type: application/json"
    ]);
    curl_setopt($ch, CURLOPT_CUSTOMREQUEST, "PUT");
    curl_setopt($ch, CURLOPT_POSTFIELDS, json_encode($data));
    $response = curl_exec($ch);
    curl_close($ch);

    $json = json_decode($response, true);
    return isset($json['content']);
}

// Generate a downloadable link from the video file (stub function)
function generateDownloadLink($video) {
    // Here, you can implement your logic to generate a link to the video
    // For example, using Telegram File API:
    $file_id = $video['file_id'];
    return "https://api.telegram.org/file/bot" . getenv('TELEGRAM_TOKEN') . "/" . $file_id;
}
?>
