<?php
require_once "config.php";

/* -----------------------------
   GitHub Temporary Mapping File
-------------------------------*/
define("GITHUB_PENDING_FILE", "pending_links.txt"); // stores SHORTID|URL temporarily

$update = json_decode(file_get_contents("php://input"), true);
if (!$update) exit;

/* -----------------------------
   SECURITY — Only OWNER_ID can use bot
-------------------------------*/
if (isset($update["message"])) {
    if ($update["message"]["chat"]["id"] != OWNER_ID) exit;
}

/* -----------------------------
   START COMMAND
-------------------------------*/
if (isset($update["message"]["text"]) && $update["message"]["text"] == "/start") {
    sendMessage(OWNER_ID, "Send a video (≤2GB) or a direct link to update.");
    exit;
}

/* ==============================
   CASE 1 — VIDEO UPDATE
============================== */
if (isset($update["message"]["video"])) {

    $video = $update["message"]["video"];
    $file_name = $video["file_name"] ?? "";
    $file_size = $video["file_size"];
    $file_id   = $video["file_id"];

    if ($file_size > MAX_FILE_SIZE) exit;

    $matched = matchTitle($file_name);
    if (!$matched) exit;

    $file_info = telegramApi("getFile", ["file_id"=>$file_id]);
    if (!$file_info["ok"]) exit;

    $file_path = $file_info["result"]["file_path"];
    $download_link = "https://api.telegram.org/file/bot".BOT_TOKEN."/".$file_path;

    updateGithubFile($matched, $download_link);
    sendMessage(OWNER_ID, "Updated $matched with video link.");
    exit;
}

/* ==============================
   CASE 2 — DIRECT LINK
   Using GitHub temporary storage
============================== */
if (isset($update["message"]["text"]) &&
    filter_var($update["message"]["text"], FILTER_VALIDATE_URL)) {

    $link = $update["message"]["text"];
    $shortId = substr(md5($link . time()), 0, 8);

    // 1. Save to GitHub pending_links.txt
    addPendingLink($shortId, $link);

    // 2. Send buttons
    $keyboard = [
        "inline_keyboard" => [
            [
                ["text"=>"Sky","callback_data"=>"Sky|$shortId"],
                ["text"=>"Willow","callback_data"=>"Willow|$shortId"]
            ],
            [
                ["text"=>"Prime1","callback_data"=>"Prime1|$shortId"],
                ["text"=>"Prime2","callback_data"=>"Prime2|$shortId"]
            ]
        ]
    ];

    sendMessage(OWNER_ID, "Select title to update:", $keyboard);
    exit;
}

/* ==============================
   BUTTON HANDLER
============================== */
if (isset($update["callback_query"])) {

    $data = $update["callback_query"]["data"];
    list($title, $shortId) = explode("|", $data);

    // 1. Read pending link from GitHub
    $link = getPendingLink($shortId);
    if (!$link) {
        telegramApi("answerCallbackQuery", [
            "callback_query_id"=>$update["callback_query"]["id"],
            "text"=>"Expired or already used. Send link again."
        ]);
        exit;
    }

    // 2. Update the selected title
    updateGithubFile($title, $link);

    // 3. Remove from pending_links.txt
    removePendingLink($shortId);

    telegramApi("answerCallbackQuery", [
        "callback_query_id"=>$update["callback_query"]["id"],
        "text"=>"Updated $title"
    ]);
    exit;
}

/* ==============================
   MATCH ENGINE (Case 1 Video Matching)
============================== */
function normalizeText($text){
    $text = strtolower($text);
    $text = str_replace([".", "-", "_"], " ", $text);
    $text = preg_replace('/\s+/', ' ', $text);
    return trim($text);
}

function matchTitle($file_name){
    $normalized = normalizeText($file_name);

    if (strpos($normalized, "the 50") !== false)
        return "50";

    $titles = ["Master Chef","Wheel of fortune","Laughter Chef"];
    foreach ($titles as $title){
        $words = explode(" ", normalizeText($title));
        $match = true;
        foreach ($words as $word){
            if (strpos($normalized, $word) === false){
                $match = false;
                break;
            }
        }
        if ($match) return $title;
    }
    return false;
}

/* ==============================
   GITHUB FUNCTIONS
==============================*/
function updateGithubFile($title,$newLink){
    $url = "https://api.github.com/repos/".GITHUB_USERNAME."/".GITHUB_REPO."/contents/".GITHUB_FILE_PATH;

    $ch = curl_init($url);
    curl_setopt($ch, CURLOPT_HTTPHEADER, [
        "Authorization: token ".GITHUB_TOKEN,
        "User-Agent: TelegramBot"
    ]);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER,true);
    $response = json_decode(curl_exec($ch),true);
    curl_close($ch);

    $content = base64_decode($response["content"]);
    $sha = $response["sha"];
    $lines = explode("\n",$content);

    for($i=0;$i<count($lines);$i++){
        if(trim($lines[$i])==$title){
            $lines[$i+1]=$newLink;
            break;
        }
    }

    $updated = base64_encode(implode("\n",$lines));

    $data=[
        "message"=>"Updated $title link",
        "content"=>$updated,
        "sha"=>$sha
    ];

    $ch=curl_init($url);
    curl_setopt($ch,CURLOPT_CUSTOMREQUEST,"PUT");
    curl_setopt($ch,CURLOPT_POSTFIELDS,json_encode($data));
    curl_setopt($ch,CURLOPT_HTTPHEADER,[
        "Authorization: token ".GITHUB_TOKEN,
        "User-Agent: TelegramBot",
        "Content-Type: application/json"
    ]);
    curl_setopt($ch,CURLOPT_RETURNTRANSFER,true);
    curl_exec($ch);
    curl_close($ch);
}

/* -----------------------------
   Pending Links Functions (Case 2)
-------------------------------*/
function addPendingLink($shortId, $link){
    $url = "https://api.github.com/repos/".GITHUB_USERNAME."/".GITHUB_REPO."/contents/".GITHUB_PENDING_FILE;

    // Get existing content
    $ch = curl_init($url);
    curl_setopt($ch, CURLOPT_HTTPHEADER, [
        "Authorization: token ".GITHUB_TOKEN,
        "User-Agent: TelegramBot"
    ]);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER,true);
    $response = json_decode(curl_exec($ch),true);
    curl_close($ch);

    if(isset($response["content"])){
        $content = base64_decode($response["content"]);
        $sha = $response["sha"];
        $lines = explode("\n",$content);
    }else{
        $lines = [];
        $sha = null;
    }

    $lines[] = "$shortId|$link";
    $updated = base64_encode(implode("\n",$lines));

    $data=[
        "message"=>"Add pending link $shortId",
        "content"=>$updated
    ];
    if($sha) $data["sha"]=$sha;

    $ch=curl_init($url);
    curl_setopt($ch,CURLOPT_CUSTOMREQUEST,"PUT");
    curl_setopt($ch,CURLOPT_POSTFIELDS,json_encode($data));
    curl_setopt($ch,CURLOPT_HTTPHEADER,[
        "Authorization: token ".GITHUB_TOKEN,
        "User-Agent: TelegramBot",
        "Content-Type: application/json"
    ]);
    curl_setopt($ch,CURLOPT_RETURNTRANSFER,true);
    curl_exec($ch);
    curl_close($ch);
}

function getPendingLink($shortId){
    $url = "https://api.github.com/repos/".GITHUB_USERNAME."/".GITHUB_REPO."/contents/".GITHUB_PENDING_FILE;

    $ch = curl_init($url);
    curl_setopt($ch, CURLOPT_HTTPHEADER, [
        "Authorization: token ".GITHUB_TOKEN,
        "User-Agent: TelegramBot"
    ]);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER,true);
    $response = json_decode(curl_exec($ch),true);
    curl_close($ch);

    if(!isset($response["content"])) return false;

    $lines = explode("\n", base64_decode($response["content"]));
    foreach($lines as $line){
        if(strpos($line,$shortId."|")===0){
            return substr($line, strlen($shortId)+1);
        }
    }
    return false;
}

function removePendingLink($shortId){
    $url = "https://api.github.com/repos/".GITHUB_USERNAME."/".GITHUB_REPO."/contents/".GITHUB_PENDING_FILE;

    $ch = curl_init($url);
    curl_setopt($ch, CURLOPT_HTTPHEADER, [
        "Authorization: token ".GITHUB_TOKEN,
        "User-Agent: TelegramBot"
    ]);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER,true);
    $response = json_decode(curl_exec($ch),true);
    curl_close($ch);

    if(!isset($response["content"])) return;

    $lines = explode("\n", base64_decode($response["content"]));
    $lines = array_filter($lines, function($line) use ($shortId){ return strpos($line,$shortId."|")!==0; });
    $updated = base64_encode(implode("\n",$lines));

    $data=[
        "message"=>"Remove pending link $shortId",
        "content"=>$updated,
        "sha"=>$response["sha"]
    ];

    $ch=curl_init($url);
    curl_setopt($ch,CURLOPT_CUSTOMREQUEST,"PUT");
    curl_setopt($ch,CURLOPT_POSTFIELDS,json_encode($data));
    curl_setopt($ch,CURLOPT_HTTPHEADER,[
        "Authorization: token ".GITHUB_TOKEN,
        "User-Agent: TelegramBot",
        "Content-Type: application/json"
    ]);
    curl_setopt($ch,CURLOPT_RETURNTRANSFER,true);
    curl_exec($ch);
    curl_close($ch);
}

/* -----------------------------
   TELEGRAM FUNCTIONS
-------------------------------*/
function telegramApi($method,$params){
    $ch=curl_init("https://api.telegram.org/bot".BOT_TOKEN."/".$method);
    curl_setopt($ch,CURLOPT_POST,true);
    curl_setopt($ch,CURLOPT_POSTFIELDS,$params);
    curl_setopt($ch,CURLOPT_RETURNTRANSFER,true);
    $res=json_decode(curl_exec($ch),true);
    curl_close($ch);
    return $res;
}

function sendMessage($chat_id,$text,$keyboard=null){
    $data=["chat_id"=>$chat_id,"text"=>$text];
    if($keyboard) $data["reply_markup"]=json_encode($keyboard);
    telegramApi("sendMessage",$data);
}
