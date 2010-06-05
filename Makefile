DESTDIR=
VERSION=3
PYTHON=2.6

install:
	install -d $(DESTDIR)/usr/bin $(DESTDIR)/usr/lib/python$(PYTHON)/site-packages/
	install -m755 src/netcfg-tray.py $(DESTDIR)/usr/bin/netcfg-tray
	install -m755 src/netcfg-tray-helper $(DESTDIR)/usr/bin/
	install -m644 src/netcfg.py $(DESTDIR)/usr/lib/python$(PYTHON)/site-packages/
	install -D -m644 src/config $(DESTDIR)/etc/xdg/netcfg-tray/config

tarball: 
	mkdir -p netcfg-tray-$(VERSION)/src 
	cp -r src LICENSE Makefile netcfg-tray-$(VERSION)
	tar -zcvf netcfg-tray-$(VERSION).tar.gz netcfg-tray-$(VERSION)
	rm -rf netcfg-tray-$(VERSION)

upload: 
	md5sum netcfg-tray-$(VERSION)*gz > MD5SUMS.$(VERSION)
	scp netcfg-tray-$(VERSION)*gz MD5SUMS.$(VERSION) archlinux.org:/srv/ftp/other/netcfg/tray/
	rm MD5SUMS.$(VERSION)

clean:
	rm -rf netcfg-tray-*
	rm MD5SUMS.*
