# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QRealTime
                                 A QGIS plugin
 This plugin connects you to Aggregate Server and do autoupdation of data to and from aggregate
                             -------------------
        begin                : 2017-08-09
        copyright            : (C) 2017 by IIRS
        email                : kotishiva@gmail.com
        git sha              : $Format:%H$
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
 This script initializes the plugin, making it known to QGIS.
"""


# noinspection PyPep8Naming
def classFactory(iface):  # pylint: disable=invalid-name
    """Load QRealTime class from file QRealTime.

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    #
    from .QRealTime import QRealTime
    return QRealTime(iface)
