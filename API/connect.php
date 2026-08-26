<?php

// Put your MySQL server address here. Example: "localhost"
$host = "";

// Put your MySQL username here. Example: "root"
$user = "";

// Put your MySQL password here. Keep it empty only if your account has no password.
$password = "";

// Put your database name here. Example: "rfid_aircraft_tools"
$database = "";

// Environment variables can override these values without changing this file.
$host = getenv("RFID_DB_HOST") ?: $host;
$user = getenv("RFID_DB_USER") ?: $user;
$password = getenv("RFID_DB_PASSWORD") ?: $password;
$database = getenv("RFID_DB_DATABASE") ?: $database;

$conn = new mysqli($host, $user, $password, $database);

if ($conn->connect_error) {
    die("Database connection failed: " . $conn->connect_error);
}

$conn->set_charset("utf8mb4");

?>
