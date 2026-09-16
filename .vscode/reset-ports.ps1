$ports = 5500, 8000

foreach ($port in $ports) {
    $connections = netstat -ano -p tcp
    foreach ($connection in $connections) {
        $fields = $connection.Trim() -split '\s+'
        if ($fields.Count -ge 5 -and $fields[0] -eq 'TCP' -and $fields[1].EndsWith(":$port") -and $fields[3] -eq 'LISTENING') {
            Stop-Process -Id ([int]$fields[-1]) -Force -ErrorAction SilentlyContinue
        }
    }
}
