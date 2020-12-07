%global  _hardened_build     1
%global  nginx_user          nginx

# gperftools exist only on selected arches
%ifnarch s390 s390x
%global with_gperftools 1
%endif

%global with_aio 1

%if 0%{?fedora} > 22
%global with_mailcap_mimetypes 1
%endif

Name:              nginx
Epoch:             1
Version:           1.12.2
Release:           1%{?dist}

Summary:           A high performance web server and reverse proxy server
Group:             System Environment/Daemons
# BSD License (two clause)
# http://www.freebsd.org/copyright/freebsd-license.html
License:           BSD
URL:               http://nginx.org/

Source0:           http://nginx.org/download/nginx-%{version}.tar.gz
Source1:           http://nginx.org/download/nginx-%{version}.tar.gz.asc
Source10:          nginx.service
Source11:          nginx.logrotate
Source12:          nginx.conf
Source13:          nginx-upgrade
Source14:          nginx-upgrade.8
Source100:         index.html
Source101:         poweredby.png
Source102:         nginx-logo.png
Source103:         404.html
Source104:         50x.html
Source200:         README.dynamic
Source210:         UPGRADE-NOTES-1.6-to-1.10

# removes -Werror in upstream build scripts.  -Werror conflicts with
# -D_FORTIFY_SOURCE=2 causing warnings to turn into errors.
Patch0:            nginx-auto-cc-gcc.patch

%if 0%{?with_gperftools}
BuildRequires:     gperftools-devel
%endif
BuildRequires:     openssl-devel
BuildRequires:     pcre-devel
BuildRequires:     zlib-devel

Requires:          nginx-filesystem = %{epoch}:%{version}-%{release}

%if 0%{?rhel} || 0%{?fedora} < 24
# Introduced at 1:1.10.0-1 to ease upgrade path. To be removed later.
Requires:          nginx-all-modules = %{epoch}:%{version}-%{release}
%endif

Requires:          openssl
Requires:          pcre
Requires(pre):     nginx-filesystem
%if 0%{?with_mailcap_mimetypes}
Requires:          nginx-mimetypes
%endif
Provides:          webserver

BuildRequires:     systemd
Requires(post):    systemd
Requires(preun):   systemd
Requires(postun):  systemd

%description
Nginx is a web server and a reverse proxy server for HTTP, SMTP, POP3 and
IMAP protocols, with a strong focus on high concurrency, performance and low
memory usage.

%package all-modules
Group:             System Environment/Daemons
Summary:           A meta package that installs all available Nginx modules
BuildArch:         noarch

Requires:          nginx-mod-http-geoip = %{epoch}:%{version}-%{release}
Requires:          nginx-mod-http-image-filter = %{epoch}:%{version}-%{release}
Requires:          nginx-mod-http-perl = %{epoch}:%{version}-%{release}
Requires:          nginx-mod-http-xslt-filter = %{epoch}:%{version}-%{release}
Requires:          nginx-mod-mail = %{epoch}:%{version}-%{release}
Requires:          nginx-mod-stream = %{epoch}:%{version}-%{release}

%description all-modules
%{summary}.
%if 0%{?rhel}
The main nginx package depends on this to ease the upgrade path. After a grace
period of several months, modules will become optional.
%endif
%if 0%{?fedora} && 0%{?fedora} < 24
The main nginx package depends on this to ease the upgrade path. Starting from
Fedora 24, modules are optional.
%endif

%package filesystem
Group:             System Environment/Daemons
Summary:           The basic directory layout for the Nginx server
BuildArch:         noarch
Requires(pre):     shadow-utils

%description filesystem
The nginx-filesystem package contains the basic directory layout
for the Nginx server including the correct permissions for the
directories.

%package mod-http-geoip
Group:             System Environment/Daemons
Summary:           Nginx HTTP geoip module
BuildRequires:     GeoIP-devel
Requires:          nginx
Requires:          GeoIP

%description mod-http-geoip
%{summary}.

%package mod-http-image-filter
Group:             System Environment/Daemons
Summary:           Nginx HTTP image filter module
BuildRequires:     gd-devel
Requires:          nginx
Requires:          gd

%description mod-http-image-filter
%{summary}.

%package mod-http-perl
Group:             System Environment/Daemons
Summary:           Nginx HTTP perl module
BuildRequires:     perl-devel
%if 0%{?fedora} >= 24
BuildRequires:     perl-generators
%endif
BuildRequires:     perl(ExtUtils::Embed)
Requires:          nginx
Requires:          perl(:MODULE_COMPAT_%(eval "`%{__perl} -V:version`"; echo $version))

%description mod-http-perl
%{summary}.

%package mod-http-xslt-filter
Group:             System Environment/Daemons
Summary:           Nginx XSLT module
BuildRequires:     libxslt-devel
Requires:          nginx

%description mod-http-xslt-filter
%{summary}.

%package mod-mail
Group:             System Environment/Daemons
Summary:           Nginx mail modules
Requires:          nginx

%description mod-mail
%{summary}.

%package mod-stream
Group:             System Environment/Daemons
Summary:           Nginx stream modules
Requires:          nginx

%description mod-stream
%{summary}.


%prep
%setup -q
%patch0 -p0

cp %{SOURCE200} .
cp %{SOURCE210} .

%if 0%{?rhel} < 8
sed -i -e 's#KillMode=.*#KillMode=process#g' %{SOURCE10}
sed -i -e 's#PROFILE=SYSTEM#HIGH:!aNULL:!MD5#' %{SOURCE12}
%endif


%build
# nginx does not utilize a standard configure script.  It has its own
# and the standard configure options cause the nginx configure script
# to error out.  This is is also the reason for the DESTDIR environment
# variable.
export DESTDIR=%{buildroot}
./configure \
    --prefix=%{_datadir}/nginx \
    --sbin-path=%{_sbindir}/nginx \
    --modules-path=%{_libdir}/nginx/modules \
    --conf-path=%{_sysconfdir}/nginx/nginx.conf \
    --error-log-path=%{_localstatedir}/log/nginx/error.log \
    --http-log-path=%{_localstatedir}/log/nginx/access.log \
    --http-client-body-temp-path=%{_localstatedir}/lib/nginx/tmp/client_body \
    --http-proxy-temp-path=%{_localstatedir}/lib/nginx/tmp/proxy \
    --http-fastcgi-temp-path=%{_localstatedir}/lib/nginx/tmp/fastcgi \
    --http-uwsgi-temp-path=%{_localstatedir}/lib/nginx/tmp/uwsgi \
    --http-scgi-temp-path=%{_localstatedir}/lib/nginx/tmp/scgi \
    --pid-path=/run/nginx.pid \
    --lock-path=/run/lock/subsys/nginx \
    --user=%{nginx_user} \
    --group=%{nginx_user} \
%if 0%{?with_aio}
    --with-file-aio \
%endif
    --with-ipv6 \
    --with-http_ssl_module \
    --with-http_v2_module \
    --with-http_realip_module \
    --with-http_addition_module \
    --with-http_xslt_module=dynamic \
    --with-http_image_filter_module=dynamic \
    --with-http_geoip_module=dynamic \
    --with-http_sub_module \
    --with-http_dav_module \
    --with-http_flv_module \
    --with-http_mp4_module \
    --with-http_gunzip_module \
    --with-http_gzip_static_module \
    --with-http_random_index_module \
    --with-http_secure_link_module \
    --with-http_degradation_module \
    --with-http_slice_module \
    --with-http_stub_status_module \
    --with-http_perl_module=dynamic \
    --with-http_auth_request_module \
    --with-mail=dynamic \
    --with-mail_ssl_module \
    --with-pcre \
    --with-pcre-jit \
    --with-stream=dynamic \
    --with-stream_ssl_module \
    --add-module=/home/mockbuild/ngx_devel_kit-0.3.1rc1 \
    --add-module=/home/mockbuild/nginx-rtmp-module-dev \
    --add-module=/home/mockbuild/ngx_http_substitutions_filter_module-0.6.4 \
    --add-module=/home/mockbuild/set-misc-nginx-module-0.32rc1 \
    --add-module=/home/mockbuild/nginx-vod-module-1.24 \
    --add-module=/home/mockbuild/nchan-1.2.6 \
%if 0%{?with_gperftools}
    --with-google_perftools_module \
%endif
    --with-debug \
    --with-cc-opt="%{optflags} $(pcre-config --cflags)" \
    --with-ld-opt="$RPM_LD_FLAGS -Wl,-E" # so the perl module finds its symbols

make %{?_smp_mflags}


%install
make install DESTDIR=%{buildroot} INSTALLDIRS=vendor

find %{buildroot} -type f -name .packlist -exec rm -f '{}' \;
find %{buildroot} -type f -name perllocal.pod -exec rm -f '{}' \;
find %{buildroot} -type f -empty -exec rm -f '{}' \;
find %{buildroot} -type f -iname '*.so' -exec chmod 0755 '{}' \;

install -p -D -m 0644 %{SOURCE10} \
    %{buildroot}%{_unitdir}/nginx.service
install -p -D -m 0644 %{SOURCE11} \
    %{buildroot}%{_sysconfdir}/logrotate.d/nginx

install -p -d -m 0755 %{buildroot}%{_sysconfdir}/nginx/conf.d
install -p -d -m 0755 %{buildroot}%{_sysconfdir}/nginx/default.d

install -p -d -m 0700 %{buildroot}%{_localstatedir}/lib/nginx
install -p -d -m 0700 %{buildroot}%{_localstatedir}/lib/nginx/tmp
install -p -d -m 0700 %{buildroot}%{_localstatedir}/log/nginx

install -p -d -m 0755 %{buildroot}%{_datadir}/nginx/html
install -p -d -m 0755 %{buildroot}%{_datadir}/nginx/modules
install -p -d -m 0755 %{buildroot}%{_libdir}/nginx/modules

install -p -m 0644 %{SOURCE12} \
    %{buildroot}%{_sysconfdir}/nginx
install -p -m 0644 %{SOURCE100} \
    %{buildroot}%{_datadir}/nginx/html
install -p -m 0644 %{SOURCE101} %{SOURCE102} \
    %{buildroot}%{_datadir}/nginx/html
install -p -m 0644 %{SOURCE103} %{SOURCE104} \
    %{buildroot}%{_datadir}/nginx/html

%if 0%{?with_mailcap_mimetypes}
rm -f %{buildroot}%{_sysconfdir}/nginx/mime.types
%endif

install -p -D -m 0644 %{_builddir}/nginx-%{version}/man/nginx.8 \
    %{buildroot}%{_mandir}/man8/nginx.8

install -p -D -m 0755 %{SOURCE13} %{buildroot}%{_bindir}/nginx-upgrade
install -p -D -m 0644 %{SOURCE14} %{buildroot}%{_mandir}/man8/nginx-upgrade.8

for i in ftdetect indent syntax; do
    install -p -D -m644 contrib/vim/${i}/nginx.vim \
        %{buildroot}%{_datadir}/vim/vimfiles/${i}/nginx.vim
done

echo 'load_module "%{_libdir}/nginx/modules/ngx_http_geoip_module.so";' \
    > %{buildroot}%{_datadir}/nginx/modules/mod-http-geoip.conf
echo 'load_module "%{_libdir}/nginx/modules/ngx_http_image_filter_module.so";' \
    > %{buildroot}%{_datadir}/nginx/modules/mod-http-image-filter.conf
echo 'load_module "%{_libdir}/nginx/modules/ngx_http_perl_module.so";' \
    > %{buildroot}%{_datadir}/nginx/modules/mod-http-perl.conf
echo 'load_module "%{_libdir}/nginx/modules/ngx_http_xslt_filter_module.so";' \
    > %{buildroot}%{_datadir}/nginx/modules/mod-http-xslt-filter.conf
echo 'load_module "%{_libdir}/nginx/modules/ngx_mail_module.so";' \
    > %{buildroot}%{_datadir}/nginx/modules/mod-mail.conf
echo 'load_module "%{_libdir}/nginx/modules/ngx_stream_module.so";' \
    > %{buildroot}%{_datadir}/nginx/modules/mod-stream.conf

%pre filesystem
getent group %{nginx_user} > /dev/null || groupadd -r %{nginx_user}
getent passwd %{nginx_user} > /dev/null || \
    useradd -r -d %{_localstatedir}/lib/nginx -g %{nginx_user} \
    -s /sbin/nologin -c "Nginx web server" %{nginx_user}
exit 0

%post
%systemd_post nginx.service

%post mod-http-geoip
if [ $1 -eq 1 ]; then
    /usr/bin/systemctl reload nginx.service >/dev/null 2>&1 || :
fi

%post mod-http-image-filter
if [ $1 -eq 1 ]; then
    /usr/bin/systemctl reload nginx.service >/dev/null 2>&1 || :
fi

%post mod-http-perl
if [ $1 -eq 1 ]; then
    /usr/bin/systemctl reload nginx.service >/dev/null 2>&1 || :
fi

%post mod-http-xslt-filter
if [ $1 -eq 1 ]; then
    /usr/bin/systemctl reload nginx.service >/dev/null 2>&1 || :
fi

%post mod-mail
if [ $1 -eq 1 ]; then
    /usr/bin/systemctl reload nginx.service >/dev/null 2>&1 || :
fi

%post mod-stream
if [ $1 -eq 1 ]; then
    /usr/bin/systemctl reload nginx.service >/dev/null 2>&1 || :
fi

%preun
%systemd_preun nginx.service

%postun
%systemd_postun nginx.service
if [ $1 -ge 1 ]; then
    /usr/bin/nginx-upgrade >/dev/null 2>&1 || :
fi

%files
%license LICENSE
%doc CHANGES README README.dynamic
%if 0%{?rhel} == 7
%doc UPGRADE-NOTES-1.6-to-1.10
%endif
%{_datadir}/nginx/html/*
%{_bindir}/nginx-upgrade
%{_sbindir}/nginx
%{_datadir}/vim/vimfiles/ftdetect/nginx.vim
%{_datadir}/vim/vimfiles/syntax/nginx.vim
%{_datadir}/vim/vimfiles/indent/nginx.vim
%{_mandir}/man3/nginx.3pm*
%{_mandir}/man8/nginx.8*
%{_mandir}/man8/nginx-upgrade.8*
%{_unitdir}/nginx.service
%config(noreplace) %{_sysconfdir}/nginx/fastcgi.conf
%config(noreplace) %{_sysconfdir}/nginx/fastcgi.conf.default
%config(noreplace) %{_sysconfdir}/nginx/fastcgi_params
%config(noreplace) %{_sysconfdir}/nginx/fastcgi_params.default
%config(noreplace) %{_sysconfdir}/nginx/koi-utf
%config(noreplace) %{_sysconfdir}/nginx/koi-win
%if ! 0%{?with_mailcap_mimetypes}
%config(noreplace) %{_sysconfdir}/nginx/mime.types
%endif
%config(noreplace) %{_sysconfdir}/nginx/mime.types.default
%config(noreplace) %{_sysconfdir}/nginx/nginx.conf
%config(noreplace) %{_sysconfdir}/nginx/nginx.conf.default
%config(noreplace) %{_sysconfdir}/nginx/scgi_params
%config(noreplace) %{_sysconfdir}/nginx/scgi_params.default
%config(noreplace) %{_sysconfdir}/nginx/uwsgi_params
%config(noreplace) %{_sysconfdir}/nginx/uwsgi_params.default
%config(noreplace) %{_sysconfdir}/nginx/win-utf
%config(noreplace) %{_sysconfdir}/logrotate.d/nginx
%attr(700,%{nginx_user},%{nginx_user}) %dir %{_localstatedir}/lib/nginx
%attr(700,%{nginx_user},%{nginx_user}) %dir %{_localstatedir}/lib/nginx/tmp
%attr(700,%{nginx_user},%{nginx_user}) %dir %{_localstatedir}/log/nginx
%dir %{_libdir}/nginx/modules

%files all-modules

%files filesystem
%dir %{_datadir}/nginx
%dir %{_datadir}/nginx/html
%dir %{_sysconfdir}/nginx
%dir %{_sysconfdir}/nginx/conf.d
%dir %{_sysconfdir}/nginx/default.d

%files mod-http-geoip
%{_datadir}/nginx/modules/mod-http-geoip.conf
%{_libdir}/nginx/modules/ngx_http_geoip_module.so

%files mod-http-image-filter
%{_datadir}/nginx/modules/mod-http-image-filter.conf
%{_libdir}/nginx/modules/ngx_http_image_filter_module.so

%files mod-http-perl
%{_datadir}/nginx/modules/mod-http-perl.conf
%{_libdir}/nginx/modules/ngx_http_perl_module.so
%dir %{perl_vendorarch}/auto/nginx
%{perl_vendorarch}/nginx.pm
%{perl_vendorarch}/auto/nginx/nginx.so

%files mod-http-xslt-filter
%{_datadir}/nginx/modules/mod-http-xslt-filter.conf
%{_libdir}/nginx/modules/ngx_http_xslt_filter_module.so

%files mod-mail
%{_datadir}/nginx/modules/mod-mail.conf
%{_libdir}/nginx/modules/ngx_mail_module.so

%files mod-stream
%{_datadir}/nginx/modules/mod-stream.conf
%{_libdir}/nginx/modules/ngx_stream_module.so

%changelog
* Wed Oct 18 2017 Luboš Uhliarik <luhliari@redhat.com> - 1:1.12.2-1
- update to upstream release 1.12.2
- Resolves: #1468584 - (CVE-2017-7529) CVE-2017-7529 nginx: Integer
  overflow in nginx range filter module leading to memory disclosure

* Mon Sep 18 2017 Luboš Uhliarik <luhliari@redhat.com> - 1:1.10.2-2
- Resolves: #1478662 - rebuild for ALPN support

* Mon Oct 31 2016 Jamie Nguyen <jamielinux@fedoraproject.org> - 1:1.10.2-1
- update to upstream release 1.10.2

* Tue May 31 2016 Jamie Nguyen <jamielinux@fedoraproject.org> - 1:1.10.1-1
- update to upstream release 1.10.1

* Sun May 15 2016 Jitka Plesnikova <jplesnik@redhat.com> - 1:1.10.0-4
- Perl 5.24 rebuild

* Sun May  8 2016 Peter Robinson <pbrobinson@fedoraproject.org> 1:1.10.0-3
- Enable AIO on aarch64 (rhbz 1258414)

* Wed Apr 27 2016 Jamie Nguyen <jamielinux@fedoraproject.org> - 1:1.10.0-2
- only Require nginx-all-modules for EPEL and current Fedora releases

* Wed Apr 27 2016 Jamie Nguyen <jamielinux@fedoraproject.org> - 1:1.10.0-1
- update to upstream release 1.10.0
- split dynamic modules into subpackages
- spec file cleanup

* Thu Feb 04 2016 Fedora Release Engineering <releng@fedoraproject.org> - 1:1.8.1-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_24_Mass_Rebuild

* Tue Jan 26 2016 Jamie Nguyen <jamielinux@fedoraproject.org> - 1:1.8.1-1
- update to upstream release 1.8.1
- CVE-2016-0747: Insufficient limits of CNAME resolution in resolver
- CVE-2016-0746: Use-after-free during CNAME response processing in resolver
- CVE-2016-0742: Invalid pointer dereference in resolver

* Sun Oct 04 2015 Jamie Nguyen <jamielinux@fedoraproject.org> - 1:1.8.0-14
- consistently use '%%global with_foo' style of logic
- remove PID file before starting nginx (#1268621)

* Fri Sep 25 2015 Ville Skyttä <ville.skytta@iki.fi> - 1:1.8.0-13
- Use nginx-mimetypes from mailcap (#1248736)
- Mark LICENSE as %%license

* Thu Sep 10 2015 Jamie Nguyen <jamielinux@fedoraproject.org> - 1:1.8.0-12
- also build with gperftools on aarch64 (#1258412)

* Wed Aug 12 2015 Nikos Mavrogiannopoulos <nmav@redhat.com> - 1:1.8.0-11
- nginx.conf: added commented-out SSL configuration directives (#1179232)

* Fri Jul 03 2015 Jamie Nguyen <jamielinux@fedoraproject.org> - 1:1.8.0-10
- switch back to /bin/kill in logrotate script due to SELinux denials

* Tue Jun 16 2015 Jamie Nguyen <jamielinux@fedoraproject.org> - 1:1.8.0-9
- fix path to png in error pages (#1232277)
- optimize png images with optipng

* Sun Jun 14 2015 Jamie Nguyen <jamielinux@fedoraproject.org> - 1:1.8.0-8
- replace /bin/kill with /usr/bin/systemctl kill in logrotate script (#1231543)
- remove After=syslog.target in nginx.service (#1231543)
- replace ExecStop with KillSignal=SIGQUIT in nginx.service (#1231543)

* Wed Jun 03 2015 Jitka Plesnikova <jplesnik@redhat.com> - 1:1.8.0-7
- Perl 5.22 rebuild

* Sun May 10 2015 Jamie Nguyen <jamielinux@fedoraproject.org> - 1:1.8.0-6
- revert previous change

* Sun May 10 2015 Jamie Nguyen <jamielinux@fedoraproject.org> - 1:1.8.0-5
- move default server to default.conf (#1220094)

* Sun May 10 2015 Jamie Nguyen <jamielinux@fedoraproject.org> - 1:1.8.0-4
- add TimeoutStopSec=5 and KillMode=mixed to nginx.service
- set worker_processes to auto
- add some common options to the http block in nginx.conf
- run nginx-upgrade on package update
- remove some redundant scriptlet commands
- listen on ipv6 for default server (#1217081)

* Wed Apr 22 2015 Jamie Nguyen <jamielinux@fedoraproject.org> - 1:1.8.0-3
- improve nginx-upgrade script

* Wed Apr 22 2015 Jamie Nguyen <jamielinux@fedoraproject.org> - 1:1.8.0-2
- add --with-pcre-jit

* Wed Apr 22 2015 Jamie Nguyen <jamielinux@fedoraproject.org> - 1:1.8.0-1
- update to upstream release 1.8.0

* Thu Apr 09 2015 Jamie Nguyen <jamielinux@fedoraproject.org> - 1:1.7.12-1
- update to upstream release 1.7.12

* Sun Feb 15 2015 Jamie Nguyen <jamielinux@fedoraproject.org> - 1:1.7.10-1
- update to upstream release 1.7.10
- remove systemd conditionals

* Wed Oct 22 2014 Jamie Nguyen <jamielinux@fedoraproject.org> - 1:1.6.2-4
- fix package ownership of directories

* Wed Oct 22 2014 Jamie Nguyen <jamielinux@fedoraproject.org> - 1:1.6.2-3
- add vim files (#1142849)

* Mon Sep 22 2014 Jamie Nguyen <jamielinux@fedoraproject.org> - 1:1.6.2-2
- create nginx-filesystem subpackage (patch from Remi Collet)
- create /etc/nginx/default.d as a drop-in directory for configuration files
  for the default server block
- clean up nginx.conf

* Wed Sep 17 2014 Jamie Nguyen <jamielinux@fedoraproject.org> - 1:1.6.2-1
- update to upstream release 1.6.2
- CVE-2014-3616 nginx: virtual host confusion (#1142573)

* Wed Aug 27 2014 Jitka Plesnikova <jplesnik@redhat.com> - 1:1.6.1-4
- Perl 5.20 rebuild

* Sun Aug 17 2014 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 1:1.6.1-3
- Rebuilt for https://fedoraproject.org/wiki/Fedora_21_22_Mass_Rebuild

* Tue Aug 05 2014 Jamie Nguyen <jamielinux@fedoraproject.org> - 1:1.6.1-2
- add logic for EPEL 7

* Tue Aug 05 2014 Jamie Nguyen <jamielinux@fedoraproject.org> - 1:1.6.1-1
- update to upstream release 1.6.1
- (#1126891) CVE-2014-3556: SMTP STARTTLS plaintext injection flaw

* Wed Jul 02 2014 Yaakov Selkowitz <yselkowi@redhat.com> - 1:1.6.0-3
- Fix FTBFS on aarch64 (#1115559)

* Sat Jun 07 2014 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 1:1.6.0-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_21_Mass_Rebuild

* Sat Apr 26 2014 Jamie Nguyen <jamielinux@fedoraproject.org> - 1:1.6.0-1
- update to upstream release 1.6.0

* Tue Mar 18 2014 Jamie Nguyen <jamielinux@fedoraproject.org> - 1:1.4.7-1
- update to upstream release 1.4.7

* Wed Mar 05 2014 Jamie Nguyen <jamielinux@fedoraproject.org> - 1:1.4.6-1
- update to upstream release 1.4.6

* Sun Feb 16 2014 Jamie Nguyen <jamielinux@fedoraproject.org> - 1:1.4.5-2
- avoid multiple index directives (#1065488)

* Sun Feb 16 2014 Jamie Nguyen <jamielinux@fedoraproject.org> - 1:1.4.5-1
- update to upstream release 1.4.5

* Wed Nov 20 2013 Peter Borsa <peter.borsa@gmail.com> - 1:1.4.4-1
- Update to upstream release 1.4.4
- Security fix BZ 1032267

* Sun Nov 03 2013 Jamie Nguyen <jamielinux@fedoraproject.org> - 1:1.4.3-1
- update to upstream release 1.4.3

* Fri Aug 09 2013 Jonathan Steffan <jsteffan@fedoraproject.org> - 1:1.4.2-3
- Add in conditionals to build for non-systemd targets

* Sat Aug 03 2013 Petr Pisar <ppisar@redhat.com> - 1:1.4.2-2
- Perl 5.18 rebuild

* Fri Jul 19 2013 Jamie Nguyen <jamielinux@fedoraproject.org> - 1:1.4.2-1
- update to upstream release 1.4.2

* Wed Jul 17 2013 Petr Pisar <ppisar@redhat.com> - 1:1.4.1-3
- Perl 5.18 rebuild

* Tue Jun 11 2013 Remi Collet <rcollet@redhat.com> - 1:1.4.1-2
- rebuild for new GD 2.1.0

* Tue May 07 2013 Jamie Nguyen <jamielinux@fedoraproject.org> - 1:1.4.1-1
- update to upstream release 1.4.1 (#960605, #960606):
  CVE-2013-2028 stack-based buffer overflow when handling certain chunked
  transfer encoding requests

* Sun Apr 28 2013 Dan Horák <dan[at]danny.cz> - 1:1.4.0-2
- gperftools exist only on selected arches

* Fri Apr 26 2013 Jamie Nguyen <jamielinux@fedoraproject.org> - 1:1.4.0-1
- update to upstream release 1.4.0
- enable SPDY module (new in this version)
- enable http gunzip module (new in this version)
- enable google perftools module and add gperftools-devel to BR
- enable debugging (#956845)
- trim changelog

* Tue Apr 02 2013 Jamie Nguyen <jamielinux@fedoraproject.org> - 1:1.2.8-1
- update to upstream release 1.2.8

* Fri Feb 22 2013 Jamie Nguyen <jamielinux@fedoraproject.org> - 1:1.2.7-2
- make sure nginx directories are not world readable (#913724, #913735)

* Sat Feb 16 2013 Jamie Nguyen <jamielinux@fedoraproject.org> - 1:1.2.7-1
- update to upstream release 1.2.7
- add .asc file

* Tue Feb 05 2013 Jamie Nguyen <jamielinux@fedoraproject.org> - 1:1.2.6-6
- use 'kill' instead of 'systemctl' when rotating log files to workaround
  SELinux issue (#889151)

* Wed Jan 23 2013 Jamie Nguyen <jamielinux@fedoraproject.org> - 1:1.2.6-5
- uncomment "include /etc/nginx/conf.d/*.conf by default but leave the
  conf.d directory empty (#903065)

* Wed Jan 23 2013 Jamie Nguyen <jamielinux@fedoraproject.org> - 1:1.2.6-4
- add comment in nginx.conf regarding "include /etc/nginf/conf.d/*.conf"
  (#903065)

* Wed Dec 19 2012 Jamie Nguyen <jamielinux@fedoraproject.org> - 1:1.2.6-3
- use correct file ownership when rotating log files

* Tue Dec 18 2012 Jamie Nguyen <jamielinux@fedoraproject.org> - 1:1.2.6-2
- send correct kill signal and use correct file permissions when rotating
  log files (#888225)
- send correct kill signal in nginx-upgrade

* Tue Dec 11 2012 Jamie Nguyen <jamielinux@fedoraproject.org> - 1:1.2.6-1
- update to upstream release 1.2.6

* Sat Nov 17 2012 Jamie Nguyen <jamielinux@fedoraproject.org> - 1:1.2.5-1
- update to upstream release 1.2.5

* Sun Oct 28 2012 Jamie Nguyen <jamielinux@fedoraproject.org> - 1:1.2.4-1
- update to upstream release 1.2.4
- introduce new systemd-rpm macros (#850228)
- link to official documentation not the community wiki (#870733)
- do not run systemctl try-restart after package upgrade to allow the
  administrator to run nginx-upgrade and avoid downtime
- add nginx man page (#870738)
- add nginx-upgrade man page and remove README.fedora
- remove chkconfig from Requires(post/preun)
- remove initscripts from Requires(preun/postun)
- remove separate configuration files in "/etc/nginx/conf.d" directory
  and revert to upstream default of a centralized nginx.conf file
  (#803635) (#842738)

* Fri Sep 21 2012 Jamie Nguyen <jamielinux@fedoraproject.org> - 1:1.2.3-1
- update to upstream release 1.2.3

* Fri Jul 20 2012 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 1:1.2.1-3
- Rebuilt for https://fedoraproject.org/wiki/Fedora_18_Mass_Rebuild

* Thu Jun 28 2012 Petr Pisar <ppisar@redhat.com> - 1:1.2.1-2
- Perl 5.16 rebuild

* Sun Jun 10 2012 Jamie Nguyen <jamielinux@fedoraproject.org> - 1:1.2.1-1
- update to upstream release 1.2.1

* Fri Jun 08 2012 Petr Pisar <ppisar@redhat.com> - 1:1.2.0-2
- Perl 5.16 rebuild

* Wed May 16 2012 Jamie Nguyen <jamielinux@fedoraproject.org> - 1:1.2.0-1
- update to upstream release 1.2.0

* Wed May 16 2012 Jamie Nguyen <jamielinux@fedoraproject.org> - 1:1.0.15-4
- add nginx-upgrade to replace functionality from the nginx initscript
  that was lost after migration to systemd
- add README.fedora to describe usage of nginx-upgrade
- nginx.logrotate: use built-in systemd kill command in postrotate script
- nginx.service: start after syslog.target and network.target
- nginx.service: remove unnecessary references to config file location
- nginx.service: use /bin/kill instead of "/usr/sbin/nginx -s" following
  advice from nginx-devel
- nginx.service: use private /tmp

* Mon May 14 2012 Jamie Nguyen <jamielinux@fedoraproject.org> - 1:1.0.15-3
- fix incorrect postrotate script in nginx.logrotate

* Thu Apr 19 2012 Jamie Nguyen <jamielinux@fedoraproject.org> - 1:1.0.15-2
- renable auto-cc-gcc patch due to warnings on rawhide

* Sat Apr 14 2012 Jamie Nguyen <jamielinux@fedoraproject.org> - 1:1.0.15-1
- update to upstream release 1.0.15
- no need to apply auto-cc-gcc patch
- add %%global _hardened_build 1

* Thu Mar 15 2012 Jamie Nguyen <jamielinux@fedoraproject.org> - 1:1.0.14-1
- update to upstream release 1.0.14
- amend some %%changelog formatting

* Tue Mar 06 2012 Jamie Nguyen <jamielinux@fedoraproject.org> - 1:1.0.13-1
- update to upstream release 1.0.13
- amend --pid-path and --log-path

* Sun Mar 04 2012 Jamie Nguyen <jamielinux@fedoraproject.org> - 1:1.0.12-5
- change pid path in nginx.conf to match systemd service file

* Sun Mar 04 2012 Jamie Nguyen <jamielinux@fedoraproject.org> - 1:1.0.12-3
- fix %%pre scriptlet

* Mon Feb 20 2012 Jamie Nguyen <jamielinux@fedoraproject.org> - 1:1.0.12-2
- update upstream URL
- replace %%define with %%global
- remove obsolete BuildRoot tag, %%clean section and %%defattr
- remove various unnecessary commands
- add systemd service file and update scriptlets
- add Epoch to accommodate %%triggerun as part of systemd migration

* Sun Feb 19 2012 Jeremy Hinegardner <jeremy at hinegardner dot org> - 1.0.12-1
- Update to 1.0.12

* Thu Nov 17 2011 Keiran "Affix" Smith <fedora@affix.me> - 1.0.10-1
- Bugfix: a segmentation fault might occur in a worker process if resolver got a big DNS response. Thanks to Ben Hawkes.
- Bugfix: in cache key calculation if internal MD5 implementation wasused; the bug had appeared in 1.0.4.
- Bugfix: the module ngx_http_mp4_module sent incorrect "Content-Length" response header line if the "start" argument was used. Thanks to Piotr Sikora.

* Thu Oct 27 2011 Keiran "Affix" Smith <fedora@affix.me> - 1.0.8-1
- Update to new 1.0.8 stable release

* Fri Aug 26 2011 Keiran "Affix" Smith <fedora@affix.me> - 1.0.5-1
- Update nginx to Latest Stable Release

* Fri Jun 17 2011 Marcela Mašláňová <mmaslano@redhat.com> - 1.0.0-3
- Perl mass rebuild

* Thu Jun 09 2011 Marcela Mašláňová <mmaslano@redhat.com> - 1.0.0-2
- Perl 5.14 mass rebuild

* Wed Apr 27 2011 Jeremy Hinegardner <jeremy at hinegardner dot org> - 1.0.0-1
- Update to 1.0.0

* Tue Feb 08 2011 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 0.8.53-6
- Rebuilt for https://fedoraproject.org/wiki/Fedora_15_Mass_Rebuild

* Sun Dec 12 2010 Jeremy Hinegardner <jeremy at hinegardner dot org> - 0.8.53.5
- Extract out default config into its own file (bug #635776)

* Sun Dec 12 2010 Jeremy Hinegardner <jeremy at hinegardner dot org> - 0.8.53-4
- Revert ownership of log dir

* Sun Dec 12 2010 Jeremy Hinegardner <jeremy at hinegardner dot org> - 0.8.53-3
- Change ownership of /var/log/nginx to be 0700 nginx:nginx
- update init script to use killproc -p
- add reopen_logs command to init script
- update init script to use nginx -q option

* Sun Oct 31 2010 Jeremy Hinegardner <jeremy at hinegardner dot org> - 0.8.53-2
- Fix linking of perl module

* Sun Oct 31 2010 Jeremy Hinegardner <jeremy at hinegardner dot org> - 0.8.53-1
- Update to new stable 0.8.53

* Sat Jul 31 2010 Jeremy Hinegardner <jeremy at hinegardner dot org> - 0.7.67-2
- add Provides: webserver (bug #619693)

* Sun Jun 20 2010 Jeremy Hinegardner <jeremy at hinegardner dot org> - 0.7.67-1
- Update to new stable 0.7.67
- fix bugzilla #591543

* Tue Jun 01 2010 Marcela Maslanova <mmaslano@redhat.com> - 0.7.65-2
- Mass rebuild with perl-5.12.0

* Mon Feb 15 2010 Jeremy Hinegardner <jeremy at hinegardner dot org> - 0.7.65-1
- Update to new stable 0.7.65
- change ownership of logdir to root:root
- add support for ipv6 (bug #561248)
- add random_index_module
- add secure_link_module

* Fri Dec 04 2009 Jeremy Hinegardner <jeremy at hinegardner dot org> - 0.7.64-1
- Update to new stable 0.7.64
