<?php

// Check if the API can connect to MySQL.
require_once "connect.php";

header("Content-Type: application/json");

echo json_encode([
    "success" => true,
    "message" => "Connexion à la base de données réussie."
], JSON_PRETTY_PRINT);

$conn->close();

?>
