# Betting Advisor - Monitoring Connection Troubleshooter for Windows
# This script diagnoses and fixes connection issues with Grafana and Prometheus

# Color definitions
$Global:ColorScheme = @{
    Success = "Green"
    Warning = "Yellow"
    Error = "Red"
    Info = "Cyan"
    Header = "Blue"
}

# Write colored output
function Write-ColorOutput {
    param(
        [string]$Text,
        [string]$Color = "White"
    )
    
    Write-Host $Text -ForegroundColor $Color
}

# Write section header
function Write-Header {
    param([string]$Text)
    
    Write-ColorOutput "`n============================================" $ColorScheme.Header
    Write-ColorOutput "  $Text" $ColorScheme.Header
    Write-ColorOutput "============================================" $ColorScheme.Header
}

# Check if command exists
function Test-CommandExists {
    param([string]$Command)
    
    return [bool](Get-Command -Name $Command -ErrorAction SilentlyContinue)
}

# Check pod status
function Test-PodStatus {
    param(
        [string]$PodPrefix,
        [string]$Namespace
    )
    
    Write-ColorOutput "`nChecking $PodPrefix status in $Namespace namespace..." $ColorScheme.Warning
    
    try {
        $pods = kubectl get pods -n $Namespace 2>$null | Select-String -Pattern $PodPrefix
        
        if ($pods.Count -eq 0) {
            Write-ColorOutput "✗ No $PodPrefix pods found in $Namespace namespace!" $ColorScheme.Error
            return $false
        }
        
        $runningPods = 0
        $totalPods = 0
        
        foreach ($pod in $pods) {
            $totalPods++
            if ($pod -match "Running") {
                $runningPods++
            }
        }
        
        if ($runningPods -eq $totalPods -and $totalPods -gt 0) {
            Write-ColorOutput "✓ All $PodPrefix pods are running ($runningPods/$totalPods)" $ColorScheme.Success
            return $true
        } 
        else {
            Write-ColorOutput "✗ Some $PodPrefix pods are not running ($runningPods/$totalPods)" $ColorScheme.Error
            
            # Show problematic pods
            Write-ColorOutput "`nProblematic pods:" $ColorScheme.Warning
            foreach ($pod in $pods) {
                if ($pod -notmatch "Running") {
                    Write-ColorOutput $pod $ColorScheme.Error
                }
            }
            
            return $false
        }
    } 
    catch {
        Write-ColorOutput "✗ Error checking pod status: $($_.Exception.Message)" $ColorScheme.Error
        return $false
    }
}

# Check service status
function Test-ServiceStatus {
    param(
        [string]$Service,
        [string]$Namespace
    )
    
    Write-ColorOutput "`nChecking $Service service in $Namespace namespace..." $ColorScheme.Warning
    
    try {
        $serviceExists = kubectl get svc -n $Namespace 2>$null | Select-String -Pattern $Service
        
        if ($serviceExists) {
            Write-ColorOutput "✓ $Service service exists" $ColorScheme.Success
            
            # Show service details
            Write-ColorOutput "`nService details:" $ColorScheme.Warning
            kubectl get svc $Service -n $Namespace -o wide
            
            return $true
        } 
        else {
            Write-ColorOutput "✗ $Service service not found!" $ColorScheme.Error
            return $false
        }
    } 
    catch {
        Write-ColorOutput "✗ Error checking service status: $($_.Exception.Message)" $ColorScheme.Error
        return $false
    }
}

# Check ingress status
function Test-IngressStatus {
    param(
        [string]$Ingress,
        [string]$Namespace
    )
    
    Write-ColorOutput "`nChecking $Ingress ingress in $Namespace namespace..." $ColorScheme.Warning
    
    try {
        $ingressExists = kubectl get ingress -n $Namespace 2>$null | Select-String -Pattern $Ingress
        
        if ($ingressExists) {
            Write-ColorOutput "✓ $Ingress ingress exists" $ColorScheme.Success
            
            # Show ingress details
            Write-ColorOutput "`nIngress details:" $ColorScheme.Warning
            kubectl get ingress $Ingress -n $Namespace -o wide
            
            # Check if address is assigned
            $address = kubectl get ingress $Ingress -n $Namespace -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>$null
            
            if ([string]::IsNullOrEmpty($address)) {
                Write-ColorOutput "✗ No IP address assigned to ingress!" $ColorScheme.Error
            } 
            else {
                Write-ColorOutput "✓ Ingress IP: $address" $ColorScheme.Success
            }
            
            return $true
        } 
        else {
            Write-ColorOutput "✗ $Ingress ingress not found!" $ColorScheme.Error
            return $false
        }
    } 
    catch {
        Write-ColorOutput "✗ Error checking ingress status: $($_.Exception.Message)" $ColorScheme.Error
        return $false
    }
}

# Set up port forwarding
function Start-PortForwarding {
    param(
        [string]$Service,
        [string]$Namespace,
        [int]$LocalPort,
        [int]$ServicePort
    )
    
    Write-ColorOutput "`nSetting up port forwarding for $Service..." $ColorScheme.Warning
    
    # Check if port is already in use
    try {
        $portInUse = Get-NetTCPConnection -LocalPort $LocalPort -ErrorAction SilentlyContinue
        
        if ($portInUse) {
            Write-ColorOutput "✗ Port $LocalPort is already in use!" $ColorScheme.Error
            Write-ColorOutput "Attempting to free the port..." $ColorScheme.Warning
            
            # Try to stop the process using the port
            try {
                $processId = (Get-Process -Id (Get-NetTCPConnection -LocalPort $LocalPort).OwningProcess).Id
                Stop-Process -Id $processId -Force
                Write-ColorOutput "✓ Process with ID $processId killed" $ColorScheme.Success
            } 
            catch {
                Write-ColorOutput "✗ Unable to free port ${LocalPort}: $($_.Exception.Message)" $ColorScheme.Error
                return $false
            }
        }
        
        # Start port forwarding
        Write-ColorOutput "Starting port forwarding: ${Service}:${ServicePort} -> localhost:${LocalPort}" $ColorScheme.Warning
        
        $job = Start-Job -ScriptBlock {
            param($svc, $ns, $lp, $sp)
            kubectl port-forward "svc/$svc" "${lp}:${sp}" -n $ns
        } -ArgumentList $Service, $Namespace, $LocalPort, $ServicePort
        
        # Wait a moment to see if it starts successfully
        Start-Sleep -Seconds 2
        
        if ($job.State -eq "Running") {
            Write-ColorOutput "✓ Port forwarding started successfully (Job ID: $($job.Id))" $ColorScheme.Success
            Write-ColorOutput "✓ You can now access $Service at http://localhost:${LocalPort}" $ColorScheme.Success
            
            # Save job ID to temp file
            $job.Id | Out-File -FilePath "$env:TEMP\$Service-portforward.txt"
            
            return $true
        } 
        else {
            Write-ColorOutput "✗ Port forwarding failed to start!" $ColorScheme.Error
            Receive-Job -Job $job  # Display any error output
            Remove-Job -Job $job -Force
            return $false
        }
    } 
    catch {
        Write-ColorOutput "✗ Error setting up port forwarding: $($_.Exception.Message)" $ColorScheme.Error
        return $false
    }
}

# Check DNS resolution
function Test-DnsResolution {
    param([string]$Hostname)
    
    Write-ColorOutput "`nChecking DNS resolution for $Hostname..." $ColorScheme.Warning
    
    try {
        $result = Resolve-DnsName -Name $Hostname -ErrorAction SilentlyContinue
        
        if ($result) {
            Write-ColorOutput "✓ DNS resolution successful for $Hostname" $ColorScheme.Success
            return $true
        } 
        else {
            Write-ColorOutput "✗ DNS resolution failed for $Hostname" $ColorScheme.Error
            
            # Try with Google DNS
            Write-ColorOutput "`nTrying with Google DNS (8.8.8.8)..." $ColorScheme.Warning
            try {
                $googleResult = Resolve-DnsName -Name $Hostname -Server 8.8.8.8 -ErrorAction SilentlyContinue
                
                if ($googleResult) {
                    Write-ColorOutput "✓ DNS resolution successful with Google DNS" $ColorScheme.Success
                    Write-ColorOutput "Consider changing your DNS server to 8.8.8.8" $ColorScheme.Warning
                } 
                else {
                    Write-ColorOutput "✗ DNS resolution failed even with Google DNS" $ColorScheme.Error
                }
            } 
            catch {
                Write-ColorOutput "✗ Error with Google DNS: $($_.Exception.Message)" $ColorScheme.Error
            }
            
            return $false
        }
    } 
    catch {
        Write-ColorOutput "✗ Error checking DNS resolution: $($_.Exception.Message)" $ColorScheme.Error
        return $false
    }
}

# Check TCP connectivity
function Test-TcpConnection {
    param(
        [string]$Hostname,
        [int]$Port,
        [int]$Timeout = 5
    )
    
    Write-ColorOutput "`nChecking connectivity to ${Hostname}:${Port}..." $ColorScheme.Warning
    
    try {
        $tcpClient = New-Object System.Net.Sockets.TcpClient
        $connection = $tcpClient.BeginConnect($Hostname, $Port, $null, $null)
        $wait = $connection.AsyncWaitHandle.WaitOne($Timeout * 1000, $false)
        
        if (!$wait) {
            $tcpClient.Close()
            Write-ColorOutput "✗ Connection timed out to ${Hostname}:${Port}" $ColorScheme.Error
            return $false
        } 
        else {
            $tcpClient.EndConnect($connection)
            $tcpClient.Close()
            Write-ColorOutput "✓ Connection successful to ${Hostname}:${Port}" $ColorScheme.Success
            return $true
        }
    } 
    catch {
        Write-ColorOutput "✗ Connection failed to ${Hostname}:${Port}: $($_.Exception.Message)" $ColorScheme.Error
        return $false
    }
}

# Main script execution
function Start-Diagnostics {
    Write-Header "BETTING ADVISOR MONITORING DIAGNOSTICS"

    # Check if kubectl is available
    Write-ColorOutput "`nChecking if kubectl is available..." $ColorScheme.Warning
    if (-not (Test-CommandExists "kubectl")) {
        Write-ColorOutput "✗ kubectl not found! This script requires kubectl to be installed." $ColorScheme.Error
        Write-ColorOutput "Please install kubectl: https://kubernetes.io/docs/tasks/tools/install-kubectl-windows/" $ColorScheme.Info
        return
    } 
    else {
        Write-ColorOutput "✓ kubectl found" $ColorScheme.Success
    }

    # Check if connected to a Kubernetes cluster
    Write-ColorOutput "`nChecking connection to Kubernetes cluster..." $ColorScheme.Warning
    try {
        $nodes = kubectl get nodes 2>$null
        if ($nodes) {
            Write-ColorOutput "✓ Connected to Kubernetes cluster" $ColorScheme.Success
            
            # Show cluster info
            Write-ColorOutput "`nCluster info:" $ColorScheme.Warning
            kubectl cluster-info
        } 
        else {
            Write-ColorOutput "✗ Not connected to a Kubernetes cluster!" $ColorScheme.Error
            return
        }
    } 
    catch {
        Write-ColorOutput "✗ Error connecting to Kubernetes cluster: $($_.Exception.Message)" $ColorScheme.Error
        return
    }

    # Check if monitoring namespace exists
    Write-ColorOutput "`nChecking if monitoring namespace exists..." $ColorScheme.Warning
    $monitoringNs = $null

    try {
        $namespaces = kubectl get namespace 2>$null
        
        if ($namespaces -match "monitoring") {
            $monitoringNs = "monitoring"
            Write-ColorOutput "✓ monitoring namespace found" $ColorScheme.Success
        } 
        else {
            Write-ColorOutput "✗ monitoring namespace not found!" $ColorScheme.Error
            
            # Check if betting-advisor namespace exists
            Write-ColorOutput "`nChecking if betting-advisor namespace exists..." $ColorScheme.Warning
            
            if ($namespaces -match "betting-advisor") {
                $monitoringNs = "betting-advisor"
                Write-ColorOutput "Using ${monitoringNs} namespace for monitoring components" $ColorScheme.Warning
            } 
            else {
                Write-ColorOutput "✗ betting-advisor namespace not found either!" $ColorScheme.Error
                
                # List available namespaces
                Write-ColorOutput "`nAvailable namespaces:" $ColorScheme.Warning
                kubectl get namespaces
                
                # Prompt for namespace
                Write-ColorOutput "`nPlease enter the namespace where monitoring components are installed:" $ColorScheme.Warning
                $monitoringNs = Read-Host
            }
        }
    } 
    catch {
        Write-ColorOutput "✗ Error checking namespaces: $($_.Exception.Message)" $ColorScheme.Error
        return
    }

    # Check Grafana components
    $grafanaPodsOk = Test-PodStatus "grafana" $monitoringNs
    $grafanaSvcOk = Test-ServiceStatus "grafana" $monitoringNs
    $grafanaIngressOk = Test-IngressStatus "grafana" $monitoringNs

    # Check Prometheus components
    $promPodsOk = Test-PodStatus "prometheus" $monitoringNs
    $promSvcOk = Test-ServiceStatus "prometheus" $monitoringNs
    $promIngressOk = Test-IngressStatus "prometheus" $monitoringNs

    # Check DNS and connectivity
    if ($grafanaIngressOk) {
        $grafanaHost = kubectl get ingress grafana -n $monitoringNs -o jsonpath='{.spec.rules[0].host}' 2>$null
        
        if (-not [string]::IsNullOrEmpty($grafanaHost)) {
            Test-DnsResolution $grafanaHost
            Test-TcpConnection $grafanaHost 80
            Test-TcpConnection $grafanaHost 443
        }
    }

    if ($promIngressOk) {
        $promHost = kubectl get ingress prometheus -n $monitoringNs -o jsonpath='{.spec.rules[0].host}' 2>$null
        
        if (-not [string]::IsNullOrEmpty($promHost)) {
            Test-DnsResolution $promHost
            Test-TcpConnection $promHost 80
            Test-TcpConnection $promHost 443
        }
    }

    # Set up port forwarding as a workaround
    Write-Header "SETTING UP LOCAL ACCESS"

    if ($grafanaSvcOk) {
        $grafanaPfOk = Start-PortForwarding "grafana" $monitoringNs 3000 3000
    } 
    else {
        $grafanaPfOk = $false
    }

    if ($promSvcOk) {
        $promPfOk = Start-PortForwarding "prometheus" $monitoringNs 9090 9090
    } 
    else {
        $promPfOk = $false
    }

    # Summary
    Write-Header "DIAGNOSTIC SUMMARY"

    Write-ColorOutput "`nGrafana Status:" $ColorScheme.Warning
    if ($grafanaPodsOk -and $grafanaSvcOk) {
        Write-ColorOutput "✓ Grafana components are running properly" $ColorScheme.Success
        
        if ($grafanaIngressOk) {
            Write-ColorOutput "✓ Grafana should be accessible via ingress: $grafanaHost" $ColorScheme.Success
        } 
        else {
            Write-ColorOutput "⚠ Grafana ingress is not configured properly" $ColorScheme.Warning
        }
        
        if ($grafanaPfOk) {
            Write-ColorOutput "✓ Grafana is now accessible at: http://localhost:3000" $ColorScheme.Success
        } 
        else {
            Write-ColorOutput "✗ Failed to set up port forwarding for Grafana" $ColorScheme.Error
        }
    } 
    else {
        Write-ColorOutput "✗ Grafana components have issues" $ColorScheme.Error
    }

    Write-ColorOutput "`nPrometheus Status:" $ColorScheme.Warning
    if ($promPodsOk -and $promSvcOk) {
        Write-ColorOutput "✓ Prometheus components are running properly" $ColorScheme.Success
        
        if ($promIngressOk) {
            Write-ColorOutput "✓ Prometheus should be accessible via ingress: $promHost" $ColorScheme.Success
        } 
        else {
            Write-ColorOutput "⚠ Prometheus ingress is not configured properly" $ColorScheme.Warning
        }
        
        if ($promPfOk) {
            Write-ColorOutput "✓ Prometheus is now accessible at: http://localhost:9090" $ColorScheme.Success
        } 
        else {
            Write-ColorOutput "✗ Failed to set up port forwarding for Prometheus" $ColorScheme.Error
        }
    } 
    else {
        Write-ColorOutput "✗ Prometheus components have issues" $ColorScheme.Error
    }

    # Recommendations
    Write-Header "RECOMMENDATIONS"

    if ($grafanaPfOk -or $promPfOk) {
        Write-ColorOutput "✓ Successfully set up local access via port forwarding" $ColorScheme.Success
        Write-ColorOutput "⚠ Port forwarding will be terminated when you close this window" $ColorScheme.Warning
        Write-ColorOutput "⚠ To keep using this method, save the following commands:" $ColorScheme.Warning
        
        if ($grafanaPfOk) {
            Write-ColorOutput "kubectl port-forward svc/grafana 3000:3000 -n $monitoringNs" $ColorScheme.Info
        }
        
        if ($promPfOk) {
            Write-ColorOutput "kubectl port-forward svc/prometheus 9090:9090 -n $monitoringNs" $ColorScheme.Info
        }
    }

    if (-not $grafanaIngressOk -or -not $promIngressOk) {
        Write-ColorOutput "`nTo fix ingress issues, try:" $ColorScheme.Warning
        Write-ColorOutput "1. Check that your ingress controller is running:"
        Write-ColorOutput "   kubectl get pods -n ingress-nginx" $ColorScheme.Info
        Write-ColorOutput "2. Verify TLS certificates are valid:"
        Write-ColorOutput "   kubectl get certificate -n $monitoringNs" $ColorScheme.Info
        Write-ColorOutput "3. Check ingress class is correctly specified:"
        Write-ColorOutput "   kubectl get ingressclass" $ColorScheme.Info
        Write-ColorOutput "4. Check Windows hosts file (C:\Windows\System32\drivers\etc\hosts) for proper DNS entries" $ColorScheme.Info
    }

    if (-not $grafanaPodsOk -or -not $promPodsOk) {
        Write-ColorOutput "`nTo fix pod issues, try:" $ColorScheme.Warning
        Write-ColorOutput "1. Check pod details for error messages:"
        Write-ColorOutput "   kubectl describe pods -l app=grafana -n $monitoringNs" $ColorScheme.Info
        Write-ColorOutput "   kubectl describe pods -l app=prometheus -n $monitoringNs" $ColorScheme.Info
        Write-ColorOutput "2. Check logs for errors:"
        Write-ColorOutput "   kubectl logs -l app=grafana -n $monitoringNs" $ColorScheme.Info
        Write-ColorOutput "   kubectl logs -l app=prometheus -n $monitoringNs" $ColorScheme.Info
    }

    Write-ColorOutput "`nDiagnostic script completed!" $ColorScheme.Success

    # Prompt to keep port forwarding running
    Write-ColorOutput "`nPress ENTER to terminate port forwarding and exit, or close this window to keep it running." $ColorScheme.Warning
    Read-Host

    # Clean up port forwarding jobs
    try {
        if (Test-Path "$env:TEMP\grafana-portforward.txt") {
            $jobId = Get-Content "$env:TEMP\grafana-portforward.txt"
            try {
                Stop-Job -Id $jobId -ErrorAction SilentlyContinue
                Remove-Job -Id $jobId -Force -ErrorAction SilentlyContinue
            } 
            catch {
                # Suppress errors
            }
            Remove-Item "$env:TEMP\grafana-portforward.txt" -Force
        }

        if (Test-Path "$env:TEMP\prometheus-portforward.txt") {
            $jobId = Get-Content "$env:TEMP\prometheus-portforward.txt"
            try {
                Stop-Job -Id $jobId -ErrorAction SilentlyContinue
                Remove-Job -Id $jobId -Force -ErrorAction SilentlyContinue
            } 
            catch {
                # Suppress errors
            }
            Remove-Item "$env:TEMP\prometheus-portforward.txt" -Force
        }
    } 
    catch {
        Write-ColorOutput "Error cleaning up port forwarding: $($_.Exception.Message)" $ColorScheme.Error
    }

    Write-ColorOutput "Port forwarding terminated. Goodbye!" $ColorScheme.Success
}

# Run the diagnostic script
Start-Diagnostics 