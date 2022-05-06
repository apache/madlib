# ------------------------------------------------------------------------------
# MADlib CMake Build Script
# ------------------------------------------------------------------------------

# -- Initializations that need to run even before project()

# For Solaris, we want to use the Sun compiler
# See http://www.cmake.org/Bug/view.php?id=8530
set(CMAKE_GENERATOR_CC  suncc gcc)
set(CMAKE_GENERATOR_CXX sunCC g++)

# -- CMake setup ---------------------------------------------------------------

project(MADlib)

# FindPostgreSQL.cmake needs at least 2.8.3. We are on the safe side and require
# the minimum version tested, which is 2.8.4.
cmake_minimum_required(VERSION 2.8.4 FATAL_ERROR)

include(ExternalProject)
include(CheckCXXCompilerFlag)

# -- Local definitions (filenames, paths, etc.) --------------------------------

# The default MADlib root directory should be "/usr/local/madlib" and not
# "/usr/local" (which is the CMake default)
if(CMAKE_INSTALL_PREFIX_INITIALIZED_TO_DEFAULT)
    set(CMAKE_INSTALL_PREFIX "/usr/local/madlib" CACHE PATH
        "Install path prefix, prepended onto install directories." FORCE
    )
endif(CMAKE_INSTALL_PREFIX_INITIALIZED_TO_DEFAULT)

set(MADLIB_VERSION_YML ${CMAKE_CURRENT_SOURCE_DIR}/src/config/Version.yml)

set(MAD_THIRD_PARTY ${CMAKE_BINARY_DIR}/third_party)

# Set the directory for tools needed during build time
set(MAD_BUILD_TOOLS ${CMAKE_CURRENT_SOURCE_DIR}/cmake)

set(EXTERNALPROJECT_LIST_SEPARATOR "~!~")

if(${CMAKE_SYSTEM_NAME} MATCHES "Linux")
    set(LINUX TRUE)
endif(${CMAKE_SYSTEM_NAME} MATCHES "Linux")

if(${CMAKE_SYSTEM_NAME} MATCHES "SunOS")
    set(SOLARIS TRUE)
endif(${CMAKE_SYSTEM_NAME} MATCHES "SunOS")

if(${CMAKE_SYSTEM_NAME} MATCHES "FreeBSD")
    set(FREEBSD TRUE)
endif(${CMAKE_SYSTEM_NAME} MATCHES "FreeBSD")

if(NOT CMAKE_BUILD_TYPE)
    set(CMAKE_BUILD_TYPE RelWithDebInfo CACHE STRING
        "Choose the type of build, options are: None Debug Release RelWithDebInfo MinSizeRel."
        FORCE)
endif(NOT CMAKE_BUILD_TYPE)

if (CXX11)
    SET(CMAKE_CXX_FLAGS_RELWITHDEBINFO "-O1 -g"
        CACHE STRING
        "Flags used by the CXX compiler during RELWITHDEBINFO builds." FORCE)
    SET(CMAKE_CXX_FLAGS_RELEASE "-O1 -DNDEBUG"
        CACHE STRING
        "Flags used by the CXX compiler during RELEASE builds." FORCE)
    SET(CMAKE_CXX_FLAGS_DEBUG  "-Og -g"
        CACHE STRING
        "Flags used by the CXX compiler during DEBUG builds." FORCE)
    SET(CMAKE_CXX_FLAGS_MINSIZEREL "-Os -DNDEBUG"
        CACHE STRING
        "Flags used by the CXX compiler during MINSIZEREL builds." FORCE)
endif(CXX11)


# The C++11 standard overlaps a lot with older versions of Boost.
# So before deciding what standard to use for the whole project, we
#  first detect Boost to see what version is on the system.
#
# C++11 is required for recent versions of Boost but will cause problems
# for older versions of Boost.  Therefore, we detect it here intstead of
# in src/CMakeLists.txt where the other 3rd party libraries are detected.
#
# https://cmake.org/cmake/help/git-stage/policy/CMP0093.html
# cmake < 3.15 does not define Boost_VERSION_MACRO but stores the version in
# Boost_VERSION in the format 104700. But cmake > 3.15 stores the version in Boost_VERSION
# in 1.47.0(x.y.z) format which is unsuitable for our comparison. So for cmake > 3.15
# we need to use Boost_VERSION_MACRO instead.
find_package(Boost)
if(Boost_FOUND)
    if(Boost_VERSION_MACRO)
        set(LOCAL_Boost_VERSION ${Boost_VERSION_MACRO})
    else(Boost_VERSION_MACRO)
        set(LOCAL_Boost_VERSION ${Boost_VERSION})
    endif(Boost_VERSION_MACRO)

    # We use BOOST_ASSERT_MSG, which only exists in Boost 1.47 and later.
    if(LOCAL_Boost_VERSION LESS 104700)
        message(STATUS "Found Boost ${Boost_VERSION_STRING}, but too old for MADlib. Will download a compatible version")
        set(Boost_FOUND FALSE)
    elseif(CXX11 AND (LOCAL_Boost_VERSION LESS 106500))
        message(STATUS "Found Boost ${Boost_VERSION_STRING}, but too old for C++11. Will download a compatible version")
        set(Boost_FOUND FALSE)
    else()
        message(STATUS "Found Boost ${Boost_VERSION_STRING}")
        if(106500 LESS LOCAL_Boost_VERSION)
            if(NOT CXX11)
                message(STATUS "Auto-enabling -DCXX11, because Boost >= v1.65 requires C++11")
                set(CXX11 TRUE)
            endif(NOT CXX11)
        endif(106500 LESS LOCAL_Boost_VERSION)
    endif()
endif(Boost_FOUND)

if(CMAKE_COMPILER_IS_GNUCC)
    # Let's store the gcc version in a variable
    execute_process(COMMAND ${CMAKE_C_COMPILER} -dumpversion
        OUTPUT_VARIABLE GNUCC_VERSION
        OUTPUT_STRIP_TRAILING_WHITESPACE)

    # A useful summary of warning options can be found here:
    # http://developer.apple.com/tools/xcode/compilercodewarnings.html
    # Note: gcc does not implicitly set _POSIX_C_SOURCE or _XOPEN_SOURCE
    # when using -std=c99.
    # http://pubs.opengroup.org/onlinepubs/9699919799/functions/V2_chap02.html#tag_15_02_01_01
    # We specify that we are POSIX.1-2001 compliant and XSI-conforming. We only
    # need to specify _XOPEN_SOURCE as _POSIX_C_SOURCE will be set implicitly.
    set(CMAKE_C_FLAGS "-pedantic -Wall -Wextra -Wno-clobbered -D_XOPEN_SOURCE=600")
    if((CMAKE_C_COMPILER_VERSION VERSION_EQUAL 5.0) OR (CMAKE_C_COMPILER_VERSION VERSION_GREATER 5.0))
        # Versions 5+ fail with the "Release" build type i.e. when optimization
        # level is -O3 or greater.
        # For CXX11, we've already limited it to -O1 for similar reasons (causes crash)
        SET(CMAKE_C_FLAGS_RELEASE "-O2 -DNDEBUG" CACHE STRING
        "Flags used by the C compiler during RELEASE builds." FORCE)
    endif()

    # See comments below for C++:
    # Weird enough, the following property is set only for C++ but not for C
    # http://stackoverflow.com/questions/3371127/use-isystem-instead-of-i-with-cmake
    set(CMAKE_INCLUDE_SYSTEM_FLAG_C "-isystem ")
elseif(CMAKE_C_COMPILER_ID STREQUAL "SunPro")
    set(CMAKE_C_FLAGS "-xc99=%all")
endif()
 
if(CMAKE_COMPILER_IS_GNUCXX)
    # Let's store the gcc version in a variable
    execute_process(COMMAND ${CMAKE_CXX_COMPILER} -dumpversion
        OUTPUT_VARIABLE GNUCXX_VERSION
        OUTPUT_STRIP_TRAILING_WHITESPACE)

    # This flag is specific for i386 and x86-64 families
    # https://gcc.gnu.org/onlinedocs/gcc-4.8.5/gcc/i386-and-x86-64-Options.html
    CHECK_CXX_COMPILER_FLAG(-mno-sse2 SSE_DISABLE_OPTIONS_AVAILABLE)
    if (SSE_DISABLE_OPTIONS_AVAILABLE)
        set(SSE_DISABLE_OPTIONS "-mno-sse2")
    endif()

    set(CMAKE_CXX_FLAGS "-fdiagnostics-show-option -Wall -Wextra -pedantic -Wconversion -Wno-long-long -Wno-clobbered ${SSE_DISABLE_OPTIONS} -fstrict-aliasing"
    )
    if (CXX11)
        set(CMAKE_CXX_FLAGS "-std=gnu++11 ${CMAKE_CXX_FLAGS}"
            CACHE STRING
            "Flags used by the compiler during all build types." FORCE)
        set(CMAKE_C_FLAGS "-std=gnu11 ${CMAKE_C_FLAGS}"
            CACHE STRING
            "Flags used by the compiler during all build types." FORCE)
    else(CXX11)
        # We need the 1998 standard plus amendments (ISO/IEC 14882:2003) plus TR1
        # Unfortunately, we only get this with gnu++98
        # Special notes:
        # - long long is not part of the C++ 1998/2003 standard, but it is such a
        # common (and useful) extension that we do not want to hear warnings about
        # it.
        set(CMAKE_CXX_FLAGS "-std=gnu++98 ${CMAKE_CXX_FLAGS}"
            CACHE STRING
            "Flags used by the compiler during all build types." FORCE)
        set(CMAKE_C_FLAGS "-std=gnu99 ${CMAKE_C_FLAGS}"
            CACHE STRING
            "Flags used by the compiler during all build types." FORCE)
        if((CMAKE_CXX_COMPILER_VERSION VERSION_EQUAL 5.0) OR (CMAKE_CXX_COMPILER_VERSION VERSION_GREATER 5.0))
            # Versions 5+ fail with the "Release" build type i.e. when optimization
            # level is -O3 or greater.
            SET(CMAKE_CXX_FLAGS_RELEASE "-O2 -DNDEBUG" CACHE STRING
            "Flags used by the CXX compiler during RELEASE builds." FORCE)
        endif()
    endif(CXX11)

    # We want to include some header files as system header files in order to
    # disable warnings. However, on Mac OS X, a CMake variable is not set
    # correctly on Mac OS X. http://www.cmake.org/Bug/view.php?id=10837
    if(APPLE)
        set(CMAKE_INCLUDE_SYSTEM_FLAG_CXX "-isystem ")
    endif(APPLE)
elseif(CMAKE_C_COMPILER_ID MATCHES "Clang")
    if(CXX11)
        SET(CMAKE_CXX_FLAGS "-stdlib=libc++ -std=c++11"
            CACHE STRING
            "Flags used by the compiler during all build types." FORCE)
    else(CXX11)
        set(CMAKE_CXX_FLAGS "-stdlib=libstdc++"
            CACHE STRING
            "Flags used by the compiler during all build types." FORCE)
    endif(CXX11)
endif(CMAKE_COMPILER_IS_GNUCXX)

if(CXX11)
    add_definitions("-D_GLIBCXX_USE_CXX11_ABI=1")
    # TODO: for recent cmake, add_compile_definitions("_GLIBCXX_USE_CXX11_ABI=1")
else(CXX11)
    add_definitions("-D_GLIBCXX_USE_CXX11_ABI=0")
    # TODO: for recent cmake, add_compile_definitions("_GLIBCXX_USE_CXX11_ABI=0")
endif(CXX11)

# force a `m4_' prefix to all builtins
if(FREEBSD)
set(M4_ARGUMENTS "-P")
else()
set(M4_ARGUMENTS "--prefix-builtins")
endif()

# -- Local includes ------------------------------------------------------------

list(APPEND CMAKE_MODULE_PATH
    "${MAD_BUILD_TOOLS}")

# -- Include all parts ---------------------------------------------------------

include(Utils)
include(LinuxUtils)
include(OSXUtils)
include(Options)

# -- Get madlib version info ----------------------------------------------------
# Read and parse Version.yml file
file(READ "${MADLIB_VERSION_YML}" _MADLIB_VERSION_CONTENTS)
string(REGEX REPLACE "^.*version:[ \t]*([^\n]*)\n.*" "\\1" MADLIB_VERSION_STRING "${_MADLIB_VERSION_CONTENTS}")

string(REPLACE "-" "_" MADLIB_VERSION_STRING_NO_HYPHEN "${MADLIB_VERSION_STRING}")

string(REGEX REPLACE "([0-9]+).*" "\\1" MADLIB_VERSION_MAJOR "${MADLIB_VERSION_STRING}")
string(REGEX REPLACE "[0-9]+\\.([0-9]+).*" "\\1" MADLIB_VERSION_MINOR "${MADLIB_VERSION_STRING}")
if("${MADLIB_VERSION_STRING}" MATCHES "[0-9]+\\.[0-9]+\\.([0-9]+).*")
    string(REGEX REPLACE "[0-9]+\\.[0-9]+\\.([0-9]+).*" "\\1" MADLIB_VERSION_PATCH "${MADLIB_VERSION_STRING}")
else()
    set(MADLIB_VERSION_PATCH 0)
endif()

# Save build time
execute_process(
    COMMAND date -u
    OUTPUT_VARIABLE MADLIB_BUILD_TIME
    OUTPUT_STRIP_TRAILING_WHITESPACE)
# Save git revision
execute_process(
    COMMAND git describe
    WORKING_DIRECTORY ${CMAKE_SOURCE_DIR}
    OUTPUT_VARIABLE MADLIB_GIT_REVISION
    ERROR_QUIET
    RESULT_VARIABLE _RESULT
    OUTPUT_STRIP_TRAILING_WHITESPACE)
if(NOT _RESULT EQUAL 0)
    set(MADLIB_GIT_REVISION "unknown")
endif(NOT _RESULT EQUAL 0)
if(CMAKE_COMPILER_IS_GNUCC)
    set(MADLIB_C_COMPILER "gcc ${GNUCC_VERSION}")
else(CMAKE_COMPILER_IS_GNUCC)
    set(MADLIB_C_COMPILER ${CMAKE_C_COMPILER_ID})
endif(CMAKE_COMPILER_IS_GNUCC)
if(CMAKE_COMPILER_IS_GNUCXX)
    set(MADLIB_CXX_COMPILER "g++ ${GNUCC_VERSION}")
else(CMAKE_COMPILER_IS_GNUCXX)
    set(MADLIB_CXX_COMPILER ${CMAKE_CXX_COMPILER_ID})
endif(CMAKE_COMPILER_IS_GNUCXX)

# -- Third-party dependencies: Find m4 -----------------------------------------
# Unfortunately, we currently rely on GNU m4 due to option --prefix-builtins,
# which is not POSIX-standardized.
if(SOLARIS)
    # Solaris ships GNU m4 as gm4, so we want to use that
    find_program(M4_BINARY gm4
        PATHS /usr/sfw/bin
        DOC "Path to the GNU m4 preprocessor."
    )
else()
    find_program(M4_BINARY m4
        PATHS /usr/local/bin /usr/bin /bin /opt/local/bin
        DOC "Path to the GNU m4 preprocessor."
    )
endif()

if(NOT M4_BINARY)
    message(FATAL_ERROR "Cannot find the m4 preprocessor.")
endif(NOT M4_BINARY)

# -- Install Read-me files and license directory -------------------------------

install(DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}/licenses"
    DESTINATION .
    COMPONENT core
    PATTERN ".DS_Store" EXCLUDE
)
install(
    FILES
        "${CMAKE_CURRENT_SOURCE_DIR}/README.md"
        "${CMAKE_CURRENT_SOURCE_DIR}/RELEASE_NOTES"
    DESTINATION doc
    COMPONENT core
)
install(
    FILES
        "${CMAKE_CURRENT_SOURCE_DIR}/NOTICE"
        "${CMAKE_CURRENT_SOURCE_DIR}/LICENSE"
    DESTINATION .
    COMPONENT core
)


# -- Add subdirectories --------------------------------------------------------

add_subdirectory(src)

# if(CMAKE_COMPILER_IS_GNUCC AND CMAKE_COMPILER_IS_GNUCXX)
#e.g., Clang/Clang++ does not work
# endif(CMAKE_COMPILER_IS_GNUCC AND CMAKE_COMPILER_IS_GNUCXX)
add_subdirectory(doc)
add_subdirectory(deploy)

# -- Install path for specific madlib version ----------------------------------
set(CMAKE_MADLIB_ROOT "${CMAKE_INSTALL_PREFIX}")
set(CMAKE_INSTALL_PREFIX "${CMAKE_MADLIB_ROOT}/Versions/${MADLIB_VERSION_STRING}")

# Move bin to old_bin if upgrading from V0.6 or earlier version
# below script finds a directory named 'bin' and copies to 'old_bin' ignoring
# any error messages (eg. if 'bin' does not exist)
install(CODE "
        EXECUTE_PROCESS(
            COMMAND find ${CMAKE_MADLIB_ROOT}/bin -type d -exec cp -RPf {} ${CMAKE_MADLIB_ROOT}/old_bin \;
            ERROR_FILE /dev/null
        )"
)
# remove the 'bin' directory to replace with symbolic link
install(CODE "
        EXECUTE_PROCESS(
            COMMAND find ${CMAKE_MADLIB_ROOT}/bin -depth -type d -exec rm -r {} \;
            ERROR_FILE /dev/null
        )"
)

# Move doc to old_doc if upgrading from V0.6 or earlier version
install(CODE "
        EXECUTE_PROCESS(
            COMMAND find ${CMAKE_MADLIB_ROOT}/doc -type d -exec cp -RPf {} ${CMAKE_MADLIB_ROOT}/old_doc \;
            ERROR_FILE /dev/null
        )"
)
install(CODE "
        EXECUTE_PROCESS(
            COMMAND find ${CMAKE_MADLIB_ROOT}/doc -depth -type d -exec rm -r {} \;
            ERROR_FILE /dev/null
        )"
)

install(CODE "
    EXECUTE_PROCESS(COMMAND ln -nsf
           ${CMAKE_INSTALL_PREFIX}
           ${CMAKE_MADLIB_ROOT}/Current
           )"
)

# Create symlink bin
install(CODE "
    EXECUTE_PROCESS(COMMAND ln -nsf
           ${CMAKE_MADLIB_ROOT}/Current/bin
           ${CMAKE_MADLIB_ROOT}/bin
           )"
)

# Create symlink doc
install(CODE "
    EXECUTE_PROCESS(COMMAND ln -nsf
           ${CMAKE_MADLIB_ROOT}/Current/doc
           ${CMAKE_MADLIB_ROOT}/doc
           )
")
