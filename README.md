This project is a RFB 3.8-based VNC implementation. 

Setup:
install all required imports using pip install -r Requirements.txt 
if this does not work manually type into command line pip install "" 
where "" is the module such as numpy or pyautogui.

Key information:
Inside of the main.py on the client side (Client folder) you will need to change the IP address to the IP of your server.
On windows this can be found by opening Command line and typing ipconfig (on windows) and then taking this value and swapping it with the one inside of the file.

How to get running?
1. On one device run the Main.py in the server side to start the server up.
2. On another device run the Main.py in the client side to start the client up.
 
This will open a window of the other screen allowing for updates from the client to the server.

To close the connections use the control key + c.

