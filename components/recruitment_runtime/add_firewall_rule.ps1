# Allow Streamlit (CandidateRanking) and Gateway inbound ports
New-NetFirewallRule -DisplayName "Allow CandidateRanking Streamlit" -Direction Inbound -Action Allow -Protocol TCP -LocalPort 8501
New-NetFirewallRule -DisplayName "Allow CandidateRanking Gateway"   -Direction Inbound -Action Allow -Protocol TCP -LocalPort 8088
Write-Host "Firewall rules for CandidateRanking (Streamlit:8501, Gateway:8088) have been added."
Read-Host "Press Enter to exit..."