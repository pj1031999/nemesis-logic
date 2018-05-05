MAKE = make
INSTALL = install

PREFIX = /usr/local

all: proto

proto:
	$(MAKE) -C $(CURDIR)/src/proto build/nemesis_pb2.py

distclean:
	$(MAKE) -C $(CURDIR)/src/proto distclean

install: proto
	@mkdir -p $(PREFIX)/sbin
	@mkdir -p $(PREFIX)/lib/nemesis/python
	$(INSTALL) -m 0755 $(CURDIR)/src/python/logic.py  $(PREFIX)/sbin/logic
	$(INSTALL) -m 0644 $(CURDIR)/src/python/database_proto.py $(PREFIX)/lib/nemesis/python
	$(INSTALL) -m 0644 $(CURDIR)/src/python/database.py $(PREFIX)/lib/nemesis/python
	$(INSTALL) -m 0644 $(CURDIR)/src/proto/default_nemesis_proto.py $(PREFIX)/lib/nemesis/python
	$(INSTALL) -m 0644 $(CURDIR)/src/proto/build/nemesis_pb2.py $(PREFIX)/lib/nemesis/python

.PHONY: all proto install distclean
