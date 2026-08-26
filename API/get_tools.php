<?php

// Get all tools shown in the desktop app.
require_once "connect.php";

header("Content-Type: application/json; charset=utf-8");
mysqli_report(MYSQLI_REPORT_ERROR | MYSQLI_REPORT_STRICT);

try {
    $result = $conn->query("
        SELECT rfid_uid, part_number, serial_number, description_tool,
               last_check, next_check, status_
        FROM tools
        ORDER BY description_tool, part_number
    ");

    $tools = [];
    while ($row = $result->fetch_assoc()) {
        $tools[] = $row;
    }

    echo json_encode($tools, JSON_PRETTY_PRINT);
} catch (Throwable $error) {
    http_response_code(500);
    echo json_encode([
        "success" => false,
        "message" => "Impossible de récupérer les outils."
    ]);
}

$conn->close();
