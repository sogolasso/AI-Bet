#!/bin/bash
#
# Betting Advisor - Monitoring Connection Troubleshooter
# This script diagnoses and fixes connection issues with Grafana and Prometheus

# Color codes for better readability
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}============================================${NC}"
echo -e "${BLUE}  BETTING ADVISOR MONITORING DIAGNOSTICS    ${NC}"
echo -e "${BLUE}============================================${NC}"

# Function to check if a command exists
command_exists() {
  command -v "$1" >/dev/null 2>&1
}

# Function to check if a pod is running
check_pod_status() {
  local pod_prefix=$1
  local namespace=$2
  
  echo -e "\n${YELLOW}Checking $pod_prefix status in $namespace namespace...${NC}"
  
  if ! kubectl get pods -n $namespace 2>/dev/null | grep -q "$pod_prefix"; then
    echo -e "${RED}✗ No $pod_prefix pods found in $namespace namespace!${NC}"
    return 1
  fi
  
  local running_pods=$(kubectl get pods -n $namespace | grep "$pod_prefix" | grep "Running" | wc -l)
  local total_pods=$(kubectl get pods -n $namespace | grep "$pod_prefix" | wc -l)
  
  if [ "$running_pods" -eq "$total_pods" ] && [ "$total_pods" -gt 0 ]; then
    echo -e "${GREEN}✓ All $pod_prefix pods are running ($running_pods/$total_pods)${NC}"
    return 0
  else
    echo -e "${RED}✗ Some $pod_prefix pods are not running ($running_pods/$total_pods)${NC}"
    
    # Show the problematic pods
    echo -e "\n${YELLOW}Problematic pods:${NC}"
    kubectl get pods -n $namespace | grep "$pod_prefix" | grep -v "Running"
    
    return 1
  fi
}

# Function to check service status
check_service() {
  local service=$1
  local namespace=$2
  
  echo -e "\n${YELLOW}Checking $service service in $namespace namespace...${NC}"
  
  if kubectl get svc -n $namespace 2>/dev/null | grep -q "$service"; then
    echo -e "${GREEN}✓ $service service exists${NC}"
    
    # Show service details
    echo -e "\n${YELLOW}Service details:${NC}"
    kubectl get svc $service -n $namespace -o wide
    return 0
  else
    echo -e "${RED}✗ $service service not found!${NC}"
    return 1
  fi
}

# Function to check ingress status
check_ingress() {
  local ingress=$1
  local namespace=$2
  
  echo -e "\n${YELLOW}Checking $ingress ingress in $namespace namespace...${NC}"
  
  if kubectl get ingress -n $namespace 2>/dev/null | grep -q "$ingress"; then
    echo -e "${GREEN}✓ $ingress ingress exists${NC}"
    
    # Show ingress details
    echo -e "\n${YELLOW}Ingress details:${NC}"
    kubectl get ingress $ingress -n $namespace -o wide
    
    # Check if the address is assigned
    local address=$(kubectl get ingress $ingress -n $namespace -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
    if [ -z "$address" ]; then
      echo -e "${RED}✗ No IP address assigned to ingress!${NC}"
    else
      echo -e "${GREEN}✓ Ingress IP: $address${NC}"
    fi
    
    return 0
  else
    echo -e "${RED}✗ $ingress ingress not found!${NC}"
    return 1
  fi
}

# Function to set up port forwarding
setup_port_forwarding() {
  local service=$1
  local namespace=$2
  local local_port=$3
  local service_port=$4
  
  echo -e "\n${YELLOW}Setting up port forwarding for $service...${NC}"
  
  # Check if something is already using the port
  if command_exists lsof; then
    if lsof -i:$local_port > /dev/null; then
      echo -e "${RED}✗ Port $local_port is already in use!${NC}"
      echo -e "${YELLOW}Trying to kill the process...${NC}"
      
      # Get the PID and kill it
      local pid=$(lsof -i:$local_port -t)
      if [ ! -z "$pid" ]; then
        kill -9 $pid
        echo -e "${GREEN}✓ Process with PID $pid killed${NC}"
      fi
    fi
  fi
  
  # Start port forwarding in the background
  echo -e "${YELLOW}Starting port forwarding: $service:$service_port -> localhost:$local_port${NC}"
  kubectl port-forward svc/$service $local_port:$service_port -n $namespace > /dev/null 2>&1 &
  
  # Store the PID
  local pid=$!
  
  # Wait a moment to see if it fails immediately
  sleep 2
  if ps -p $pid > /dev/null; then
    echo -e "${GREEN}✓ Port forwarding started successfully (PID: $pid)${NC}"
    echo -e "${GREEN}✓ You can now access $service at http://localhost:$local_port${NC}"
    echo $pid > /tmp/$service-portforward.pid
    return 0
  else
    echo -e "${RED}✗ Port forwarding failed to start!${NC}"
    return 1
  fi
}

# Function to check DNS resolution
check_dns() {
  local host=$1
  
  echo -e "\n${YELLOW}Checking DNS resolution for $host...${NC}"
  
  if command_exists nslookup; then
    nslookup $host > /dev/null 2>&1
    local result=$?
    
    if [ $result -eq 0 ]; then
      echo -e "${GREEN}✓ DNS resolution successful for $host${NC}"
      return 0
    else
      echo -e "${RED}✗ DNS resolution failed for $host${NC}"
      
      # Suggest using alternative DNS
      echo -e "\n${YELLOW}Trying with Google DNS (8.8.8.8)...${NC}"
      nslookup $host 8.8.8.8 > /dev/null 2>&1
      local google_result=$?
      
      if [ $google_result -eq 0 ]; then
        echo -e "${GREEN}✓ DNS resolution successful with Google DNS${NC}"
        echo -e "${YELLOW}Consider changing your DNS server to 8.8.8.8${NC}"
      else
        echo -e "${RED}✗ DNS resolution failed even with Google DNS${NC}"
      fi
      
      return 1
    fi
  else
    echo -e "${RED}✗ nslookup command not found, cannot check DNS${NC}"
    return 1
  fi
}

# Function to check connectivity
check_connectivity() {
  local host=$1
  local port=$2
  
  echo -e "\n${YELLOW}Checking connectivity to $host:$port...${NC}"
  
  if command_exists nc; then
    nc -z -w 5 $host $port > /dev/null 2>&1
    local result=$?
    
    if [ $result -eq 0 ]; then
      echo -e "${GREEN}✓ Connection successful to $host:$port${NC}"
      return 0
    else
      echo -e "${RED}✗ Connection failed to $host:$port${NC}"
      return 1
    fi
  elif command_exists telnet; then
    echo -e "quit" | telnet $host $port > /dev/null 2>&1
    local result=$?
    
    if [ $result -eq 0 ]; then
      echo -e "${GREEN}✓ Connection successful to $host:$port${NC}"
      return 0
    else
      echo -e "${RED}✗ Connection failed to $host:$port${NC}"
      return 1
    fi
  else
    echo -e "${RED}✗ Neither nc nor telnet command found, cannot check connectivity${NC}"
    return 1
  fi
}

# Main execution starts here
echo -e "\n${YELLOW}Checking if kubectl is available...${NC}"
if ! command_exists kubectl; then
  echo -e "${RED}✗ kubectl not found! This script requires kubectl to be installed.${NC}"
  exit 1
else
  echo -e "${GREEN}✓ kubectl found${NC}"
fi

# Check if we're connected to a Kubernetes cluster
echo -e "\n${YELLOW}Checking connection to Kubernetes cluster...${NC}"
if ! kubectl get nodes &> /dev/null; then
  echo -e "${RED}✗ Not connected to a Kubernetes cluster!${NC}"
  exit 1
else
  echo -e "${GREEN}✓ Connected to Kubernetes cluster${NC}"
  
  # Show cluster info
  echo -e "\n${YELLOW}Cluster info:${NC}"
  kubectl cluster-info | head -n 2
fi

# Check if monitoring namespace exists
echo -e "\n${YELLOW}Checking if monitoring namespace exists...${NC}"
if ! kubectl get namespace | grep -q "monitoring"; then
  echo -e "${RED}✗ monitoring namespace not found!${NC}"
  
  # Check if betting-advisor namespace exists
  echo -e "\n${YELLOW}Checking if betting-advisor namespace exists...${NC}"
  if kubectl get namespace | grep -q "betting-advisor"; then
    MONITORING_NS="betting-advisor"
    echo -e "${YELLOW}Using ${MONITORING_NS} namespace for monitoring components${NC}"
  else
    echo -e "${RED}✗ betting-advisor namespace not found either!${NC}"
    
    # List available namespaces
    echo -e "\n${YELLOW}Available namespaces:${NC}"
    kubectl get namespaces
    
    # Prompt for namespace
    echo -e "\n${YELLOW}Please enter the namespace where monitoring components are installed:${NC}"
    read MONITORING_NS
  fi
else
  MONITORING_NS="monitoring"
  echo -e "${GREEN}✓ monitoring namespace found${NC}"
fi

# Check Grafana components
check_pod_status "grafana" $MONITORING_NS
GRAFANA_PODS_OK=$?

check_service "grafana" $MONITORING_NS
GRAFANA_SVC_OK=$?

check_ingress "grafana" $MONITORING_NS
GRAFANA_INGRESS_OK=$?

# Check Prometheus components
check_pod_status "prometheus" $MONITORING_NS
PROM_PODS_OK=$?

check_service "prometheus" $MONITORING_NS
PROM_SVC_OK=$?

check_ingress "prometheus" $MONITORING_NS
PROM_INGRESS_OK=$?

# Check DNS and connectivity
if [ $GRAFANA_INGRESS_OK -eq 0 ]; then
  GRAFANA_HOST=$(kubectl get ingress grafana -n $MONITORING_NS -o jsonpath='{.spec.rules[0].host}')
  if [ ! -z "$GRAFANA_HOST" ]; then
    check_dns $GRAFANA_HOST
    check_connectivity $GRAFANA_HOST 80
    check_connectivity $GRAFANA_HOST 443
  fi
fi

if [ $PROM_INGRESS_OK -eq 0 ]; then
  PROM_HOST=$(kubectl get ingress prometheus -n $MONITORING_NS -o jsonpath='{.spec.rules[0].host}')
  if [ ! -z "$PROM_HOST" ]; then
    check_dns $PROM_HOST
    check_connectivity $PROM_HOST 80
    check_connectivity $PROM_HOST 443
  fi
fi

# Set up port forwarding as a workaround if needed
echo -e "\n${BLUE}============================================${NC}"
echo -e "${BLUE}  SETTING UP LOCAL ACCESS                   ${NC}"
echo -e "${BLUE}============================================${NC}"

if [ $GRAFANA_SVC_OK -eq 0 ]; then
  setup_port_forwarding "grafana" $MONITORING_NS 3000 3000
  GRAFANA_PF_OK=$?
else
  GRAFANA_PF_OK=1
fi

if [ $PROM_SVC_OK -eq 0 ]; then
  setup_port_forwarding "prometheus" $MONITORING_NS 9090 9090
  PROM_PF_OK=$?
else
  PROM_PF_OK=1
fi

# Summary
echo -e "\n${BLUE}============================================${NC}"
echo -e "${BLUE}  DIAGNOSTIC SUMMARY                        ${NC}"
echo -e "${BLUE}============================================${NC}"

echo -e "\n${YELLOW}Grafana Status:${NC}"
if [ $GRAFANA_PODS_OK -eq 0 ] && [ $GRAFANA_SVC_OK -eq 0 ]; then
  echo -e "${GREEN}✓ Grafana components are running properly${NC}"
  
  if [ $GRAFANA_INGRESS_OK -eq 0 ]; then
    echo -e "${GREEN}✓ Grafana should be accessible via ingress: ${GRAFANA_HOST}${NC}"
  else
    echo -e "${YELLOW}⚠ Grafana ingress is not configured properly${NC}"
  fi
  
  if [ $GRAFANA_PF_OK -eq 0 ]; then
    echo -e "${GREEN}✓ Grafana is now accessible at: http://localhost:3000${NC}"
  else
    echo -e "${RED}✗ Failed to set up port forwarding for Grafana${NC}"
  fi
else
  echo -e "${RED}✗ Grafana components have issues${NC}"
fi

echo -e "\n${YELLOW}Prometheus Status:${NC}"
if [ $PROM_PODS_OK -eq 0 ] && [ $PROM_SVC_OK -eq 0 ]; then
  echo -e "${GREEN}✓ Prometheus components are running properly${NC}"
  
  if [ $PROM_INGRESS_OK -eq 0 ]; then
    echo -e "${GREEN}✓ Prometheus should be accessible via ingress: ${PROM_HOST}${NC}"
  else
    echo -e "${YELLOW}⚠ Prometheus ingress is not configured properly${NC}"
  fi
  
  if [ $PROM_PF_OK -eq 0 ]; then
    echo -e "${GREEN}✓ Prometheus is now accessible at: http://localhost:9090${NC}"
  else
    echo -e "${RED}✗ Failed to set up port forwarding for Prometheus${NC}"
  fi
else
  echo -e "${RED}✗ Prometheus components have issues${NC}"
fi

echo -e "\n${BLUE}============================================${NC}"
echo -e "${BLUE}  RECOMMENDATIONS                           ${NC}"
echo -e "${BLUE}============================================${NC}"

if [ $GRAFANA_PF_OK -eq 0 ] || [ $PROM_PF_OK -eq 0 ]; then
  echo -e "${GREEN}✓ Successfully set up local access via port forwarding${NC}"
  echo -e "${YELLOW}⚠ Port forwarding will be terminated when you close this terminal${NC}"
  echo -e "${YELLOW}⚠ To keep using this method, save the following commands:${NC}"
  
  if [ $GRAFANA_PF_OK -eq 0 ]; then
    echo -e "${BLUE}kubectl port-forward svc/grafana 3000:3000 -n $MONITORING_NS${NC}"
  fi
  
  if [ $PROM_PF_OK -eq 0 ]; then
    echo -e "${BLUE}kubectl port-forward svc/prometheus 9090:9090 -n $MONITORING_NS${NC}"
  fi
fi

if [ $GRAFANA_INGRESS_OK -eq 1 ] || [ $PROM_INGRESS_OK -eq 1 ]; then
  echo -e "\n${YELLOW}To fix ingress issues, try:${NC}"
  echo -e "1. Check that your ingress controller is running:"
  echo -e "${BLUE}   kubectl get pods -n ingress-nginx${NC}"
  echo -e "2. Verify TLS certificates are valid:"
  echo -e "${BLUE}   kubectl get certificate -n $MONITORING_NS${NC}"
  echo -e "3. Check ingress class is correctly specified:"
  echo -e "${BLUE}   kubectl get ingressclass${NC}"
fi

if [ $GRAFANA_PODS_OK -eq 1 ] || [ $PROM_PODS_OK -eq 1 ]; then
  echo -e "\n${YELLOW}To fix pod issues, try:${NC}"
  echo -e "1. Check pod details for error messages:"
  echo -e "${BLUE}   kubectl describe pods -l app=grafana -n $MONITORING_NS${NC}"
  echo -e "${BLUE}   kubectl describe pods -l app=prometheus -n $MONITORING_NS${NC}"
  echo -e "2. Check logs for errors:"
  echo -e "${BLUE}   kubectl logs -l app=grafana -n $MONITORING_NS${NC}"
  echo -e "${BLUE}   kubectl logs -l app=prometheus -n $MONITORING_NS${NC}"
fi

echo -e "\n${GREEN}Diagnostic script completed!${NC}"

# Prompt to keep port forwarding running
echo -e "\n${YELLOW}Press ENTER to terminate port forwarding and exit, or CTRL+C to keep it running and exit the script manually.${NC}"
read -r

# Clean up port forwarding processes
if [ -f /tmp/grafana-portforward.pid ]; then
  kill $(cat /tmp/grafana-portforward.pid) 2>/dev/null
  rm /tmp/grafana-portforward.pid
fi

if [ -f /tmp/prometheus-portforward.pid ]; then
  kill $(cat /tmp/prometheus-portforward.pid) 2>/dev/null
  rm /tmp/prometheus-portforward.pid
fi

echo -e "${GREEN}Port forwarding terminated. Goodbye!${NC}" 