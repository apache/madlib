# Remove existing soft links
find $RPM_INSTALL_PREFIX/madlib/bin -depth -type l -exec rm {} \; 2>/dev/null
find $RPM_INSTALL_PREFIX/madlib/doc -depth -type l -exec rm {} \; 2>/dev/null
find $RPM_INSTALL_PREFIX/madlib/Current -depth -type l -exec rm {} \; 2>/dev/null


# RPM version is setup with underscore replaced for hyphen but
# the actual version contains a hyphen. The symlink created on disk
# is with a hyphen instead of the underscore.
MADLIB_VERSION_NO_HYPHEN=%{_madlib_version}
MADLIB_VERSION="${MADLIB_VERSION_NO_HYPHEN/_/-}"
ln -nsf $RPM_INSTALL_PREFIX/madlib/Versions/$MADLIB_VERSION $RPM_INSTALL_PREFIX/madlib/Current
ln -nsf $RPM_INSTALL_PREFIX/madlib/Current/bin $RPM_INSTALL_PREFIX/madlib/bin
ln -nsf $RPM_INSTALL_PREFIX/madlib/Current/doc $RPM_INSTALL_PREFIX/madlib/doc
