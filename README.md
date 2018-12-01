<h1> Welcome to QRealTime plugin</h1>
<img src="https://user-images.githubusercontent.com/5653512/40710547-8e30b57c-6416-11e8-8c48-3075bd63e68b.jpg" alt="flowchart">

QRealTime Plugin allows you to:
<ul>
<li> Create new survey form directly from GIS layers in QGIS </li>
<li> Synchronise data from ODK Aggregate server </li>
<li> Import data from ODK Aggregate server </li>
</ul>

<h2>Getting Started</h2>
<h3>Installation</h3>
Prerequisites:
<ul>
<li> QGIS 3.x </li>
</ul>

Installation steps:
<ol>
<li>Open Plugin Manager and search for QRealTime plugin and install it.</li>
<li>And restart QGIS so that changes in environment take effect.
<li>If after restarting QGIS still there is problem related to PyXForm then manually install pyxform library to python3 by using following:
<br/> 3a. Open command prompt/terminal and go to installation directory of QGIS.
<br/> 3b. Run <code>osgeo4w.bat</code>
<br/> 3c. Run <code>py3_env</code>
<br/> 3d. Run following:
<br/> &nbsp;&nbsp; - Windows: <code>python3 -m pip install pyxform --user</code>.
<br/> &nbsp;&nbsp; - MacOS: <code>sudo pip3 install pyxform</code>
<br/> Note: If <code>pip</code> in not recognised (as in the case of QGIS 3.4) use <code>easy_install</code> instead.
<br/> 3e. And restart QGIS so that changes in environment take effect.
</ol>

<h3>Configuration:</h3>

From the main menu choose **Plugins --> QRealTime --> QRealTime Setting**
<br/>
Enter ODK aggregate url (required). Other fields are optional. _Sync time_ is also required in case of data sync.
<br/>
If you don't have ODK Aggregate server access or want to install your own aggregate server,  <a href="http://docs.opendatakit.org/aggregate-guide/"> then visit </a>

<br/>
<img src="https://user-images.githubusercontent.com/5653512/45092573-7a69c280-b133-11e8-9b01-6b8c9f48a8c6.png" alt="settings">


<br/>
Right click over any existing layer --> QRealTIme and choose desired option: 
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
<h2> Please cite us: </h2>
<a href="https://zenodo.org/badge/latestdoi/99995529"><img src="https://zenodo.org/badge/99995529.svg" alt="DOI"></a></li>


