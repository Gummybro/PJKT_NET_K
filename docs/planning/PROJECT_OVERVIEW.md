# Network Knight
### AI-Assisted Cybersecurity Log Monitoring and Threat Detection System

## 1. Project Overview

Network Knight is an AI-assisted cybersecurity monitoring system designed to help small businesses, organizations, and educational environments monitor system activity and identify potential security threats.

The system collects security logs from computers and servers, analyzes events, identifies suspicious behavior, and presents important findings through a centralized security dashboard.

The primary goal is to make cybersecurity monitoring more accessible, understandable, and affordable without requiring users to operate complicated enterprise-level SIEM platforms.

## 2. Project Objectives

- Collect security logs from different operating systems.
- Centralize log information in one monitoring platform.
- Identify suspicious activity through detection rules.
- Assign severity levels to detected security events.
- Provide understandable explanations of potential threats.
- Display security events through an interactive dashboard.
- Help administrators investigate suspicious activity.

## 3. Proposed System Architecture

Network Knight is designed around the following components:

1. **Log Collector:** Collects security logs from computers, servers, and other supported systems.
2. **Log Reader and Parser:** Extracts useful information, including timestamps, usernames, IP addresses, and event descriptions.
3. **Database:** Stores collected events, detection results, and alerts.
4. **Threat Detection Engine:** Analyzes events and identifies suspicious behavior.
5. **Risk Classification:** Assigns Low, Medium, High, or Critical severity levels.
6. **AI Helper:** Provides explanations and contextual information about detected threats.
7. **Backend:** Connects the system components and handles application logic.
8. **Dashboard:** Displays security statistics, events, warnings, and alerts.

## 4. Technology Stack

The final technology stack will be documented according to the technologies actually implemented in the project.

The proposed development direction includes:

- Frontend: React
- Backend: Python / FastAPI
- Database: To be finalized
- Detection: Rule-based analysis and machine-learning techniques
- AI: AI-assisted threat explanations
- Deployment: Local environment using Proxmox or a supported computer environment

## 5. Core Security Detection Examples

The system is intended to identify suspicious activities such as:

- Multiple failed login attempts.
- Unusual login activity.
- Suspicious IP addresses.
- Unexpected privilege changes.
- Abnormal system activity.
- Potential brute-force attacks.

Detection results should include supporting event information so administrators can understand why an alert was generated.

## 6. Installation and Setup

Installation instructions depend on the final implementation and its dependencies.

The intended local development environment is a Windows computer.

General setup process:

1. Install the required development tools.
2. Extract the Network Knight project.
3. Open the project directory.
4. Install the frontend and backend dependencies.
5. Configure the database and application settings.
6. Start the backend service.
7. Start the frontend dashboard.
8. Open the dashboard in a web browser.

Refer to the actual project configuration files for verified installation commands.

## 7. How the System Works

The intended workflow is:

1. A computer or server generates security logs.
2. Network Knight receives the available log information.
3. The parser extracts relevant fields.
4. The database stores the processed events.
5. The detection engine analyzes the events.
6. Suspicious activity generates an alert.
7. The risk classification component assigns a severity.
8. The dashboard displays the event and its associated information.
9. The AI Helper can provide additional explanations where implemented.

## 8. Project Structure

The final directory structure depends on the actual implementation.

The project is expected to organize its components into logical areas such as:

- Frontend application
- Backend services
- Log collection
- Detection engine
- Database configuration
- AI integration
- Documentation
- Testing resources

## 9. Testing and Evaluation

The project will be evaluated using controlled security-event simulations.

Proposed tests include:

- Generating repeated failed login attempts.
- Testing normal login activity.
- Generating suspicious event sequences.
- Verifying severity classification.
- Confirming that alerts appear in the dashboard.
- Checking whether collected events are stored correctly.
- Measuring processing time and dashboard response time.

Testing should distinguish between actual system detections and manually generated demonstration events.

## 10. Security and Privacy

Network Knight is intended to handle potentially sensitive security information.

Important considerations include:

- Restricting access to collected logs.
- Protecting stored credentials.
- Validating incoming log data.
- Securing communication between components.
- Avoiding unnecessary storage of personal information.
- Preventing unauthorized access to administrative functionality.

## 11. Current Development Status

Network Knight is being developed as a senior design project.

The project will progress through the following stages:

- Requirements and project definition.
- Cybersecurity and SIEM research.
- Log source identification.
- Threat detection research.
- AI component selection.
- Technology selection.
- System architecture.
- Dashboard development.
- Implementation and integration.
- Testing and evaluation.

Individual features should be considered complete only after they have been implemented and tested.

## 12. Future Development

Potential future improvements include:

- Support for additional operating systems.
- More advanced anomaly detection.
- Improved AI-assisted investigations.
- Real-time monitoring.
- Email or other notification integrations.
- Additional security detection rules.
- Multi-user access management.
- Expanded reporting capabilities.

## 13. Project Team

- Terrynn Armstrong
- Arif Anik
- Emily Koss
- Tyler Thomas

**Project:** Network Knight  
**Institution:** Gannon University  
**Course:** CIS 457 – Senior Design

---

*Network Knight – AI-Assisted Cybersecurity Log Monitoring and Threat Detection System.*
