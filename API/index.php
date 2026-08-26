<?php

// Show basic information when the API link is opened.
header("Content-Type: application/json");

echo json_encode([
    "project" => "RFID Aircraft Tool Tracking API",
    "context" => "Academic internship prototype",
    "version" => "1.0",
    "status" => "ONLINE",
    // Keep the public developer name here.
    "developer" => "XIAD00",
    "endpoints" => [
        "/get_tools.php",
        "/add_tool.php?uid=XXXX",
        "/test_db.php"
    ]
], JSON_PRETTY_PRINT);

?>
