Name:         perl-NOCpulse-OracleDB
Version: 	  1.28.23
Release:      1%{?dist}
Summary:      Perl modules for NOCpulse Oracle database access
URL:          https://fedorahosted.org/spacewalk
Source0:      https://fedorahosted.org/releases/s/p/spacewalk/%{name}-%{version}.tar.gz
BuildArch:    noarch
Requires:     perl(:MODULE_COMPAT_%(eval "`%{__perl} -V:version`"; echo $version))
BuildRequires: perl(NOCpulse::Debug) perl(NOCpulse::Config) perl(NOCpulse::Utils::XML) perl(NOCpulse::Object)
BuildRequires: perl(RHN::DB)
BuildRequires: perl(DBI) perl(ExtUtils::MakeMaker)
Group:        Development/Libraries
License:      GPLv2
Buildroot:    %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)

%description
NOCpulse provides application, network, systems and transaction monitoring,
coupled with a comprehensive reporting system including availability,
historical and trending reports in an easy-to-use browser interface.

This package provides an API for accessing NOCpulse Oracle databases.

%prep
%setup -q

%build
%{__perl} Makefile.PL INSTALLDIRS=vendor OPTIMIZE="$RPM_OPT_FLAGS"
make %{?_smp_mflags}

%install
rm -rf $RPM_BUILD_ROOT
make pure_install PERL_INSTALL_ROOT=$RPM_BUILD_ROOT

find $RPM_BUILD_ROOT -type f -name .packlist -exec rm -f {} \;
find $RPM_BUILD_ROOT -type f -name '*.bs' -size 0 -exec rm -f {} \;
find $RPM_BUILD_ROOT -depth -type d -exec rmdir {} 2>/dev/null \;

%{_fixperms} $RPM_BUILD_ROOT/*

%check
make test

%clean
rm -rf $RPM_BUILD_ROOT

%files
%defattr(-,root,root,-)
%{perl_vendorlib}/NOCpulse/*

%changelog
* Mon Oct 03 2011 Michael Mraka <michael.mraka@redhat.com> 1.28.23-1
- fixed misspelled table name

* Fri Sep 30 2011 Michael Mraka <michael.mraka@redhat.com> 1.28.22-1
- 741782 - replaced aliases with table names

* Thu Aug 11 2011 Jan Pazdziora 1.28.21-1
- The column names are always uppercase, due to the FetchHashKeyName setting.

* Tue Mar 22 2011 Michael Mraka <michael.mraka@redhat.com> 1.28.20-1
- fixed segmentation fault in use NOCpulse::DBRecord

* Tue Mar 22 2011 Miroslav Suchý <msuchy@redhat.com> 1.28.19-1
- add missing buildrequires

* Fri Mar 18 2011 Michael Mraka <michael.mraka@redhat.com> 1.28.18-1
- fixed input values (PG)
- fixed sysdate error (PG)
- replaced aliases with table names (PG)
- reuse RHN:DB for db connection in DBRecord.pm (PG)
- reuse RHN:DB for db connection in OracleDB.pm (PG)

* Thu Sep 17 2009 Miroslav Suchý <msuchy@redhat.com> 1.28.17-1
- remove of dead code

* Mon Jul 20 2009 Devan Goodwin <dgoodwin@redhat.com> 1.28.16-1
- Dropping unecessary perl-NOCpulse-OracleDB build requires.
  (dgoodwin@redhat.com)

* Mon May 11 2009 Miroslav Suchý <msuchy@redhat.com> 1.28.13-1
- 499568 - allow LoadOneFrom to accept binded params

* Wed Jan 28 2009 Dennis Gilmore <dennis@ausil.us> 1.28.12-1
- BR perl(ExtUtils::MakeMaker)

* Tue Jan 13 2009 Miroslav Suchý <msuchy@redhat.com> 1.28.11-1
- 479161 - explicitly call disconnect

* Tue Oct 21 2008 Miroslav Suchý <msuchy@redhat.com> 1.28.10-1
- 467441 - fix namespace

* Tue Sep  2 2008 Miroslav Suchý <msuchy@redhat.com> 1.28.3-1
- spec cleanup for Fedora

* Wed May 28 2008 Jan Pazdziora 1.28.2-12
- rebuild in dist.cvs
