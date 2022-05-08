
plexon: 128.120.197.198
tilt  : 128.120.197.189

Below my email signature, I've included some information for getting PlexNet set up. When you refer to the below ideas (in the steps below my email signature), please note that the “PlexNetLocal.exe”, “PlexNetRemote.exe”, and “PlexClient.dll” all come bundled with the installation of the specific version of the OmniPlex software which the customer is using. These files can be found at “C-->Program Files (x86) -->Plexon Inc-->OmniPlex”. Please be sure to use these specific versions of these files when considering the below ideas.

Quick Start for PlexNet:

1) Start OmniPlex and begin data acquisition normally.
2) Run PlexNetLocal.exe
3) Write down the IP address shown in PlexNetLocal.
4) Copy PlexNetRemote.exe and PlexClient.dll to the remote PC.
5) On the remote PC, run PlexNetRemote.exe.
6) In PlexNetRemote, click “PlexNet Server Address and Port.”
7) Enter the IP address that you wrote down in step 3 (from PlexNetLocal).
8) Click OK.
9) Click “Connect.”
10)You should see messages indicating that PlexNetRemote is connected and that data is being received.
a. The MMF bar populating/updating indicates that data’s flowing. Also, a non-zero “kb/s” value indicates that data is flowing.
11) At this point, you can run an online client on the remote machine, which will receive data just as if it were running on the same PC as OmniPlex.  
a. In PlexNetRemote, the “Data Transfer Options” allow you to configure things like which continuous channels are sent over PlexNet. Most clients don’t need things like the wideband continuous data, so by default those channels are not sent over PlexNet. Note that you have to click “Connect” before PlexNetRemote will let you see the Data Transfer Options.  
If you’re interested in WB and/or SPKC data getting to PlexNet Remote, you also have to go to OmniPlex Server and do these steps:
    1. Stop Data acquisition.
    2. Click Online Client Options. [ConfigureOnline Client Options]
    3. Set the sampling rate to 40,000 Hz. (default is 1000).
    4. Make sure “Enable Online Client access…” is checked.
12) When you are done running clients on the remote machine, click Disconnect in PlexNetRemote.

After this first-time setup, just perform steps 1,2,5,9 to start, and 11,12 to shut down. You don’t need to re-enter the IP address in PlexNetRemote, unless the IP address of the local PC changes. To keep things simple, on the remote machine place PlexNetRemote.exe and PlexClient.dll in the same folder as your client programs. This avoids issues with the client not being able to find PlexClient.dll, or finding the wrong version.

Some settings that should generally not need to be changed:
If for some reason the default of port 6000 is not acceptable, for example, the network administrator has blocked or reserved it, find out what port number is available and enter that value in both PlexNetLocal and PlexNetRemote.

Leave the protocol set to the default of TCP/IP in both Local and Remote. Only change this setting to UDP if the remote machine does not support TCP/IP, which is rare.
