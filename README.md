<h1> Welcome to QRealTime plugin</h1>
<img src="https://user-images.githubusercontent.com/5653512/84229819-252cc300-ab08-11ea-8cc3-74f9f1d3f1df.png" alt="flowchart">


QRealTime Plugin allows you to:
<ul>
<li> Create new survey form directly from GIS layers in QGIS </li>
<li> Synchronise data from ODK Aggregate server or KoboToobox server</li>
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
<br/> Here you have two tabs one for Aggregate and another for KoboToolbox
Choose one of the tab and Enter url (required). Other fields are optional.
<br/>
You can create free account in <a href="https://www.kobotoolbox.org/">KoboToolbox server </a> and if you want to install your own aggregate server, <a href="http://docs.opendatakit.org/aggregate-guide/"> then visit </a>
<br/>
<img src="https://user-images.githubusercontent.com/5653512/67921427-aa90e200-fbcd-11e9-874b-fc1fae692fe0.png" alt="settings">


<br/>
Right click over any existing layer --> QRealTime and choose desired option: 
<br/>Make Online (To Create new form), import (to import data of existing form), sync(to automatically update your layer)
<br/>If you want to import data from already existing form (created without using our plugin) do ensure that the name of the geometry field is 'GEOMETRY','location' or 'gps. Other geometry field names are currently not supported.
<br/>
<img src="https://user-images.githubusercontent.com/5653512/45092639-be5cc780-b133-11e8-8ee1-d3fb258cbf16.png" alt="options">

<br/>
QRealTime plugin is capable of converting QGIS layer into data collection form. To design a data collection form for humanitarian crisis, we have to create appropriate vector layer. For the demonstration purpose, you can create the shapefile with following fields:
<br/>
<img src="https://user-images.githubusercontent.com/9129316/33984020-2d6d7170-e0dc-11e7-8458-c9c2feb275b6.png" alt="tables">

<br/>
If you are not sure how to create  value map in QGIS,<a href= "http://www.northrivergeographic.com/archives/qgis-and-value-maps"> Visit this link </a>
<br/>
The following video demonstrates, how to use the QRealTime Plugin:
<br/>
<iframe width="560" height="315" src="https://www.youtube.com/embed/zmr2CC5G-m4" frameborder="0" allow="autoplay; encrypted-media" allowfullscreen></iframe>
<br/>


