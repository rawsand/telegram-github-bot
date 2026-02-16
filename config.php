<?php
/* Read secrets from Render environment variables */
define("BOT_TOKEN", getenv("BOT_TOKEN"));
define("OWNER_ID", getenv("OWNER_ID"));
define("GITHUB_TOKEN", getenv("GITHUB_TOKEN"));
define("GITHUB_USERNAME", getenv("GITHUB_USERNAME"));
define("GITHUB_REPO", getenv("GITHUB_REPO"));
define("GITHUB_FILE_PATH", "links.txt");

/* Max video size 2GB */
define("MAX_FILE_SIZE", 2 * 1024 * 1024 * 1024);
