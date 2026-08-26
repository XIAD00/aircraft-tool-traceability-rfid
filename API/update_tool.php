<?php

// Update the information of one tool.
require_once "connect.php";

header("Content-Type: application/json; charset=utf-8");
mysqli_report(MYSQLI_REPORT_ERROR | MYSQLI_REPORT_STRICT);

function update_response($status, $payload)
{
    http_response_code($status);
    echo json_encode($payload);
    exit();
}

function update_text($data, $key, $maxLength)
{
    $value = trim((string) ($data[$key] ?? ""));
    return $value !== "" && strlen($value) <= $maxLength ? $value : null;
}

function update_date_is_valid($value)
{
    $date = DateTime::createFromFormat("!Y-m-d", $value);
    return $date && $date->format("Y-m-d") === $value;
}

if ($_SERVER["REQUEST_METHOD"] !== "POST") {
    header("Allow: POST");
    update_response(405, ["success" => false, "message" => "Méthode non autorisée."]);
}

$data = json_decode(file_get_contents("php://input"), true);

if (!is_array($data)) {
    update_response(400, ["success" => false, "message" => "Corps JSON invalide."]);
}

$uid = update_text($data, "rfid_uid", 50);
$partNumber = update_text($data, "part_number", 50);
$serialNumber = update_text($data, "serial_number", 50);
$description = update_text($data, "description_tool", 255);
$lastCheck = trim((string) ($data["last_check"] ?? ""));
$nextCheck = trim((string) ($data["next_check"] ?? ""));
$status = strtoupper(trim((string) ($data["status_"] ?? "")));
$allowedStatuses = ["AVAILABLE", "BORROWED", "MAINTENANCE", "CALIBRATION_DUE"];

if (
    !$uid ||
    !$partNumber ||
    !$serialNumber ||
    !$description ||
    !update_date_is_valid($lastCheck) ||
    !update_date_is_valid($nextCheck) ||
    !in_array($status, $allowedStatuses, true)
) {
    update_response(400, ["success" => false, "message" => "Données de l'outil invalides."]);
}

try {
    $exists = $conn->prepare("SELECT 1 FROM tools WHERE rfid_uid = ?");
    $exists->bind_param("s", $uid);
    $exists->execute();
    $toolExists = $exists->get_result()->num_rows === 1;
    $exists->close();

    if (!$toolExists) {
        update_response(404, ["success" => false, "message" => "Outil introuvable."]);
    }

    $stmt = $conn->prepare("
        UPDATE tools
        SET part_number = ?,
            serial_number = ?,
            description_tool = ?,
            last_check = ?,
            next_check = ?,
            status_ = ?
        WHERE rfid_uid = ?
    ");
    $stmt->bind_param(
        "sssssss",
        $partNumber,
        $serialNumber,
        $description,
        $lastCheck,
        $nextCheck,
        $status,
        $uid
    );
    $stmt->execute();
    $stmt->close();

    update_response(200, [
        "success" => true,
        "message" => "Outil mis à jour."
    ]);
} catch (mysqli_sql_exception $error) {
    if ((int) $error->getCode() === 1062) {
        update_response(409, [
            "success" => false,
            "message" => "Ce numéro de série existe déjà."
        ]);
    }

    update_response(500, [
        "success" => false,
        "message" => "Impossible de modifier l'outil."
    ]);
}
