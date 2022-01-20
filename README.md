<h1> Welcome to QRealTime Plugin Development Version</h1>
<img src="https://user-images.githubusercontent.com/5653512/84229819-252cc300-ab08-11ea-8cc3-74f9f1d3f1df.png" alt="flowchart">


QRealTime Plugin allows you to:
<ul>
<li> Create new survey form directly from GIS layers in QGIS </li>
<li> Synchronise data from ODK Aggregate, KoboToobox, and ODK Central servers</li>
<li> Import data from  server </li>
</ul>

<h2>Getting Started</h2>
<h3>Installation</h3>
Prerequisites:
<ul>
<li> QGIS installed </li>
</ul>

Installation steps:
<ol>
<li>Open Plugin Manager and search for QRealTime plugin and install it.</li>
<li>And restart QGIS so that changes in environment take effect.</li>
</ol>

<h3>Configuration:</h3>

From the main menu choose **Plugins --> QRealTime --> QRealTime Setting**
<br/> Here you have three tabs one for Aggregate, KoboToolBox, and Central
Choose one of the tabs and Enter url (required). Other fields are optional.
<br/><br/>
You can install your own aggregate server <a href="http://docs.opendatakit.org/aggregate-guide/"> here </a> <br/>
You can create a free account in KoboToolbox <a href="https://www.kobotoolbox.org/"> here </a> <br/>
You can set up ODK Central <a href="https://docs.getodk.org/central-setup/"> here </a> <br/><br/>
![QRealTimePic](https://user-images.githubusercontent.com/42852481/149683859-4c0db7ec-0c80-4a1e-b59a-1a69f9129547.png)

<h3>Using the Plugin:</h3>

<br/>
Right click over any existing layer --> QRealTime and choose desired option: 
<br/><br/>Make Online (to create new form), import (to import data of existing form), sync (to automatically update your layer)
<br/><br/>If you want to import data from already existing form (created without using our plugin) do ensure that the name of the geometry field is 'GEOMETRY', 'location', or 'gps'. Other geometry field names are currently not supported.
<br/><br/>
<img src="https://user-images.githubusercontent.com/5653512/45092639-be5cc780-b133-11e8-8ee1-d3fb258cbf16.png" alt="options">

<br/>
QRealTime plugin is capable of converting QGIS layer into data collection form. To design a data collection form for humanitarian crisis, we have to create appropriate vector layer. For the demonstration purpose, you can create the shapefile with following fields:
<br/><br/>
<img src="https://user-images.githubusercontent.com/9129316/33984020-2d6d7170-e0dc-11e7-8458-c9c2feb275b6.png" alt="tables">

<h3>Resources:</h3>

<br/>
If you are not sure how to create  value map in QGIS, visit this <a href= "http://www.northrivergeographic.com/archives/qgis-and-value-maps"> link </a>
<br/><br/>
For a tutorial on how to use the QRealTime Plugin, check out this video:
<br/>
https://www.youtube.com/watch?v=62oqJE0pgIY
<br/>
