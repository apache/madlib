# Get the RedHat/CentOS version
macro(rh_version OUT_VERSION)
    if(EXISTS "/etc/redhat-release")
        file(READ "/etc/redhat-release" _REDHAT_RELEASE_CONTENT)
        string(REGEX REPLACE "[^0-9.]*([0-9.]+)[^0-9.]*\$" "\\1" ${OUT_VERSION}
            "${_REDHAT_RELEASE_CONTENT}"
        )
    else(EXISTS "/etc/redhat-release")
        set(${OUT_VERSION} "${OUT_VERSION}-NOTFOUND")
    endif(EXISTS "/etc/redhat-release")

    if(EXISTS "/etc/photon-release")
        file(READ "/etc/photon-release" _PHOTON_RELEASE_CONTENT)
        string(REGEX REPLACE "VMware Photon OS ([0-9.]+)[0-9.]*$" "\\1"
        ${OUT_VERSION}
            "${_PHOTON_RELEASE_CONTENT}"
        )
    endif(EXISTS "/etc/photon-release")
endmacro(rh_version)

# Get the Debian version
# DEB_OUT_VERSION will have a number if /etc/issue exists, with an entry for Debian.
# DEB_OUT_VERSION will have 'DEB_OUT_VERSION-NOTFOUND' if /etc/issue does not exist.
# DEB_OUT_VERSION will be empty if some distribution which has /etc/issue, but not Debian in it.
macro(debian_version DEB_OUT_VERSION)
    if(EXISTS "/etc/issue")
        file(READ "/etc/issue" _DEB_RELEASE_CONTENT)
        string(REGEX REPLACE "Debian[^0-9.]*([0-9.]+)[^0-9.]*\$" "\\1"
        ${DEB_OUT_VERSION}
            "${_DEB_RELEASE_CONTENT}"
        )
    else(EXISTS "/etc/issue")
        set(${DEB_OUT_VERSION} "${DEB_OUT_VERSION}-NOTFOUND")
    endif(EXISTS "/etc/issue")
endmacro(debian_version)

