<?php

// Find an employee by matricule before a transaction.
require_once "connect.php";

header("Content-Type: application/json; charset=utf-8");
mysqli_report(MYSQLI_REPORT_ERROR | MYSQLI_REPORT_STRICT);

function employee_response($status, $payload)
{
    http_response_code($status);
    echo json_encode($payload);
    exit();
}

if ($_SERVER["REQUEST_METHOD"] !== "GET") {
    header("Allow: GET");
    employee_response(405, ["success" => false, "message" => "Méthode non autorisée."]);
}

$matricule = isset($_GET["matricule"])
    ? strtoupper(trim($_GET["matricule"]))
    : "";

if (
    $matricule === "" ||
    strlen($matricule) > 20 ||
    !preg_match('/^[A-Z0-9._-]+$/', $matricule)
) {
    employee_response(400, [
        "success" => false,
        "message" => "Format du matricule invalide."
    ]);
}

try {
    $stmt = $conn->prepare("
        SELECT matricule, first_name, last_name, department, service
        FROM employees
        WHERE matricule = ?
    ");
    $stmt->bind_param("s", $matricule);
    $stmt->execute();
    $employee = $stmt->get_result()->fetch_assoc();
    $stmt->close();

    if (!$employee) {
        employee_response(404, [
            "success" => false,
            "message" => "Matricule inconnu."
        ]);
    }

    employee_response(200, [
        "success" => true,
        "employee" => $employee
    ]);
} catch (Throwable $error) {
    employee_response(500, [
        "success" => false,
        "message" => "Impossible de vérifier l'employé."
    ]);
}
