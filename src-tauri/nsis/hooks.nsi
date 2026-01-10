; TimeBrief NSIS Installer Hooks
; This script handles cleanup during uninstall

!macro NSIS_HOOK_PREUNINSTALL
  ; Ask user if they want to remove app data
  MessageBox MB_YESNO "Do you want to remove all TimeBrief data (settings, database, logs)?$\n$\nClick 'No' to keep your data for a future reinstall." IDYES removeData IDNO keepData
  
  removeData:
    ; Remove TimeBrief data directory
    RMDir /r "$PROFILE\.voice_time"
    
    ; Remove any leftover config files
    Delete "$LOCALAPPDATA\TimeBrief\*.*"
    RMDir "$LOCALAPPDATA\TimeBrief"
    
    ; Clean up any log files
    Delete "$LOCALAPPDATA\com.timebrief.desktop\*.*"
    RMDir /r "$LOCALAPPDATA\com.timebrief.desktop"
    
    Goto done
    
  keepData:
    ; User chose to keep data
    
  done:
!macroend
