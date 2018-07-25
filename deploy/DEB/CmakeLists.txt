# ------------------------------------------------------------------------------
# Packaging with Debian
# ------------------------------------------------------------------------------
#
# Important: Set variables using set(... PARENT_SCOPE), so that the scope of the
# definition extends to the parent scope


# Get information about the environment

# -- Set Debian package specific variables ---------------------------------------
# get the architecture of Deb package. The name of the architecture is not
# always the same with ${CMAKE_SYSTEM_PROCESSOR}
if(NOT CPACK_DEBIAN_PACKAGE_ARCHITECTURE)
    execute_process(COMMAND dpkg --print-architecture
        OUTPUT_VARIABLE arch OUTPUT_STRIP_TRAILING_WHITESPACE)
      set(CPACK_DEBIAN_PACKAGE_ARCHITECTURE "${arch}" PARENT_SCOPE)
endif()

set(CPACK_DEBIAN_PACKAGE_VERSION "${MADLIB_VERSION_STRING}" PARENT_SCOPE)
set(CPACK_DEBIAN_PACKAGE_MAINTAINER "dev@madlib.apache.org" PARENT_SCOPE)
set(CPACK_PACKAGING_INSTALL_PREFIX "/usr/local/madlib/Versions/${MADLIB_VERSION_STRING}" PARENT_SCOPE)
