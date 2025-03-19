# Betting Advisor Monitoring Diagnostic Scripts

These scripts help diagnose and fix connection issues with the Betting Advisor monitoring stack (Grafana and Prometheus).

## Diagnostic Scripts

We provide two versions of the diagnostic script:

1. **Linux/MacOS (Bash)**: `monitor_connection.sh`
2. **Windows (PowerShell)**: `monitor_connection.ps1`

Both scripts perform the same functions but are optimized for their respective operating systems.

## What These Scripts Do

The diagnostic scripts automatically:

1. **Check your Kubernetes connection** and cluster status
2. **Verify monitoring components** (Grafana and Prometheus):
   - Check if pods are running
   - Verify services exist
   - Confirm ingress configurations
3. **Test connectivity**:
   - DNS resolution
   - Connection to ports 80/443
4. **Set up port forwarding** to access components locally
5. **Provide recommendations** for fixing common issues

## Prerequisites

- **kubectl** command-line tool installed and configured
- Access to a Kubernetes cluster where the Betting Advisor is deployed

## Usage

### For Linux/MacOS Users

```bash
# Make the script executable
chmod +x monitor_connection.sh

# Run the script
./monitor_connection.sh
```

### For Windows Users

```powershell
# Open PowerShell as Administrator
# Set execution policy (if needed)
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Run the script
.\monitor_connection.ps1
```

## Troubleshooting Common Issues

### DNS Resolution Problems

If the script reports DNS resolution issues:

1. Try using Google DNS (8.8.8.8) or Cloudflare DNS (1.1.1.1)
2. For Windows users, check your hosts file (`C:\Windows\System32\drivers\etc\hosts`)
3. Verify your DNS settings with your network administrator

### Ingress Issues

If ingress components aren't working:

1. Check if your ingress controller is running:
   ```
   kubectl get pods -n ingress-nginx
   ```
2. Verify TLS certificates:
   ```
   kubectl get certificate -n monitoring
   ```
3. Check the ingress class:
   ```
   kubectl get ingressclass
   ```

### Pod Status Issues

If pods are not running:

1. Check pod details:
   ```
   kubectl describe pods -l app=grafana -n monitoring
   ```
2. Check logs:
   ```
   kubectl logs -l app=grafana -n monitoring
   ```

## Port Forwarding

The scripts automatically set up port forwarding for local access:

- Grafana: http://localhost:3000
- Prometheus: http://localhost:9090

**Note:** Port forwarding terminates when the script ends. To keep it running continuously, either:
1. Keep the terminal window open, or
2. Run the port-forwarding commands separately:
   ```
   kubectl port-forward svc/grafana 3000:3000 -n monitoring
   kubectl port-forward svc/prometheus 9090:9090 -n monitoring
   ```

## Support

If you continue to experience issues after running these diagnostic scripts, please contact your DevOps team or file an issue in the project repository. 