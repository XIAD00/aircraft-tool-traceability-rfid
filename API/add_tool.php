<?php

// Add a new tool to the database.
require_once "connect.php";

header("Content-Type: application/json; charset=utf-8");
mysqli_report(MYSQLI_REPORT_ERROR | MYSQLI_REPORT_STRICT);

function tool_response($status, $payload)
{
    http_response_code($status);
    echo json_encode($payload);
    exit();
}

function tool_text($data, $key, $maxLength)
{
    $value = trim((string) ($data[$key] ?? ""));
    return $value !== "" && strlen($value) <= $maxLength ? $value : null;
}

function tool_date_is_valid($value)
{
    $date = DateTime::createFromFormat("!Y-m-d", $value);
    return $date && $date->format("Y-m-d") === $value;
}

if ($_SERVER["REQUEST_METHOD"] !== "POST") {
    header("Allow: POST");
    tool_response(405, ["success" => false, "message" => "Méthode non autorisée."]);
}

$data = json_decode(file_get_contents("php://input"), true);

if (!is_array($data)) {
    tool_response(400, ["success" => false, "message" => "Corps JSON invalide."]);
}

$uid = tool_text($data, "rfid_uid", 50);
$partNumber = tool_text($data, "part_number", 50);
$serialNumber = tool_text($data, "serial_number", 50);
$description = tool_text($data, "description_tool", 255);
$lastCheck = trim((string) ($data["last_check"] ?? ""));
$nextCheck = trim((string) ($data["next_check"] ?? ""));
$status = strtoupper(trim((string) ($data["status_"] ?? "")));
$allowedStatuses = ["AVAILABLE", "BORROWED", "MAINTENANCE", "CALIBRATION_DUE"];

if (
    !$uid ||
    !$partNumber ||
    !$serialNumber ||
    !$description ||
    !tool_date_is_valid($lastCheck) ||
    !tool_date_is_valid($nextCheck) ||
    !in_array($status, $allowedStatuses, true)
) {
    tool_response(400, ["success" => false, "message" => "Données de l'outil invalides."]);
}

try {
    $stmt = $conn->prepare("
        INSERT INTO tools (
            rfid_uid,
            part_number,
            serial_number,
            description_tool,
            last_check,
            next_check,
            status_
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ");
    $stmt->bind_param(
        "sssssss",
        $uid,
        $partNumber,
        $serialNumber,
        $description,
        $lastCheck,
        $nextCheck,
        $status
    );
    $stmt->execute();
    $stmt->close();

    tool_response(201, [
        "success" => true,
        "message" => "Outil ajouté."
    ]);
} catch (mysqli_sql_exception $error) {
    if ((int) $error->getCode() === 1062) {
        tool_response(409, [
            "success" => false,
            "message" => "L'UID ou le numéro de série existe déjà."
        ]);
    }

    tool_response(500, [
        "success" => false,
        "message" => "Impossible d'ajouter l'outil."
    ]);
}
