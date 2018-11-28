<h1> Welcome to QRealTime plugin</h1>
<img src="https://user-images.githubusercontent.com/5653512/40710547-8e30b57c-6416-11e8-8c48-3075bd63e68b.jpg" alt="flowchart">

QRealTime Plugin allows you to:
<UL>
<LI > Create new survey form directly from GIS layers in QGIS </LI>
<LI > Synchronise data from ODK agregate server </LI>
<LI > Import data from ODK aggregate server </LI> </UL>

<h2> Getting Started </h2>
<h3> Installation:</h3>
This is for advance user you can download it from github directly and put it on your plugin directory.Make sure you  are downloading odk-central branch.
There can be problem in some PCs related to PyXForm installation. 
Manually install pyxform library  to python3 by using following command:<br>
<b>windows :<i>python3 -m pip install pyxform --user </i><br><i>MacOS: sudo pip3 install pyxform</i></b>

And restart QGIS so that changes in enviroment take effect.
  
<h3>Configuration:</h3>

From the main menu choose Plugins --> QRealTime --> QRealTime Setting
<br>
Enter ODK aggregat url (required), other fields are optional, sync time is also required in case of data sync.
<br>
If you don't have ODK Aggregate server access or want to install your own aggregate server,  <a href="http://docs.opendatakit.org/aggregate-guide/"> then visit </a>

<br>
<img src="https://user-images.githubusercontent.com/5653512/45092573-7a69c280-b133-11e8-9b01-6b8c9f48a8c6.png" alt="settings">


<br>
Right click over any existing layer --> QRealTIme and choose desired option: 
<br>Make Online (To Create new form), import (to import data of existing form), sync(to automatically update your layer)
<br>If you want to import data from already existing form (created without using our plugin) do ensure that the name of the geometry field is 'GEOMETRY','location' or 'gps. Other geometry field names are currently not supported.
<br>
<img src="https://user-images.githubusercontent.com/5653512/45092639-be5cc780-b133-11e8-8ee1-d3fb258cbf16.png" alt="options">

<br>
QRealTime plugin is capable of converting QGIS layer into data collection form. To design a data collection form for humanitarian crisis, we have to create appropriate vector layer. For the demonstration purpose, you can create the shapefile with following fields:
<br>
<img src="https://user-images.githubusercontent.com/9129316/33984020-2d6d7170-e0dc-11e7-8458-c9c2feb275b6.png" alt="tables">

<br>
If you are not sure how to create  value map in QGIS,<a href= "http://www.northrivergeographic.com/archives/qgis-and-value-maps"> Visit this link </a>
<br>
Following video demonstarte, how to use QRealTime Plugin:
<br>
<iframe width="560" height="315" src="https://www.youtube.com/embed/zmr2CC5G-m4" frameborder="0" allow="autoplay; encrypted-media" allowfullscreen></iframe>
<br>

