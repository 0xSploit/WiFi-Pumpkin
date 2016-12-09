#!/bin/bash

for ARCHITECTURE in i386 amd64; do

VERSION=$(date +%Y%m%d)
DEB_ROOT="deb_tmp/wifi-pumpkin_${VERSION}_$ARCHITECTURE"
INSTALL_PATH=/usr/share/WiFi-Pumpkin
if [ ! -d "deb_tmp" ]; then
  mkdir -p deb_tmp
fi
mkdir -p ${DEB_ROOT}${INSTALL_PATH}
mkdir -p ${DEB_ROOT}/usr/share/applications

tar cf - --exclude=deb_tmp --exclude=./.git . | (cd ${DEB_ROOT}${INSTALL_PATH} && tar xvf - > /dev/null)

cp wifi-pumpkin.desktop ${DEB_ROOT}/usr/share/applications/wifi-pumpkin.desktop

mkdir -p ${DEB_ROOT}/DEBIAN
SIZE=$(du -sb ${DEB_ROOT}${INSTALL_PATH} | cut -f1 | awk '{print $1/1024}')

###### Start of the DEBIAN/control file ######
cat > $DEB_ROOT/DEBIAN/control << EOF
Package: wifi-pumpkin
Version: $VERSION
Priority: optional
Installed-Size: $SIZE
Architecture: $ARCHITECTURE
Maintainer: Marcos Nesster <mh4root@gmail.com>
Depends: python-pip, libffi-dev, libssl-dev, libxml2-dev, libxslt1-dev, zlib1g-dev, libarchive-dev, build-essential, libnetfilter-queue-dev, python-qt4, python-scapy, hostapd, rfkill, python-dev, git, libpcap-dev
Description: WiFi-Pumpkin
 A tool for creating a WiFi-Hotspot and executing MitM-Attacks
EOF
###### END of the DEBIAN/control file ######

###### Start of the DEBIAN/postinst file ######
cat > ${DEB_ROOT}/DEBIAN/postinst << EOF
#!/bin/bash
pip install -r $INSTALL_PATH/requirements.txt
if which update-alternatives >/dev/null; then
        update-alternatives --install /usr/bin/wifi-pumpkin wifi-pumpkin $INSTALL_PATH/wifi-pumpkin 1 > /dev/null
    else
        ln -sfT $INSTALL_PATH/wifi-pumpkin /usr/bin/wifi-pumpkin
    fi
    chmod +x $INSTALL_PATH/wifi-pumpkin
EOF
###### END of the DEBIAN/postinst file ######

chmod 0755 ${DEB_ROOT}/DEBIAN/postinst

cd deb_tmp
dpkg-deb --build wifi-pumpkin_${VERSION}_${ARCHITECTURE}
cd ..

done
