#!/usr/bin/env bash

##############################################################################
##
##  Gradle startup script for UNIX
##
##############################################################################

# Add default JVM options here. You can also use JAVA_OPTS and GRADLE_OPTS to pass JVM options to this script.
DEFAULT_JVM_OPTS="-Xmx64m" "-Xms64m"

# Use the maximum available, or set MAX_FD != -1 to use that value.
MAX_FD="maximum"

# OS specific support (must be 'true' or 'false').
cygwin=false
msys=false
darwin=false
nonstop=false
case "`uname`" in
  CYGWIN* )
    cygwin=true
    ;;
  Darwin* )
    darwin=true
    ;;
  MINGW* )
    msys=true
    ;;
  NONSTOP* )
    nonstop=true
    ;;
esac

# Determine the Java command to use to start the JVM.
if [ -n "$JAVA_HOME" ] ; then
  if [ -x "$JAVA_HOME/jre/sh/java" ] ; then
    # IBM's JDK on AIX uses strange locations for the executables
    JAVACMD="$JAVA_HOME/jre/sh/java"
  else
    JAVACMD="$JAVA_HOME/bin/java"
  fi
  if [ ! -x "$JAVACMD" ] ; then
    die "ERROR: JAVA_HOME is set to an invalid directory: $JAVA_HOME

Please set the JAVA_HOME variable in your environment to match the
location of your Java installation."
  fi
else
  JAVACMD="java"
  which java >/dev/null 2>&1 || die "ERROR: JAVA_HOME is not set and no 'java' command could be found in your PATH.

Please set the JAVA_HOME variable in your environment to match the
location of your Java installation."
fi

# Increase the maximum file descriptors if we can.
if [ "$cygwin" = "false" -a "$darwin" = "false" -a "$nonstop" = "false" ] ; then
  MAX_FD_LIMIT=`ulimit -H -n`
  if [ $? -eq 0 ] ; then
    if [ "$MAX_FD" = "maximum" -o "$MAX_FD" = "max" ] ; then
      MAX_FD="$MAX_FD_LIMIT"
    fi
    ulimit -n $MAX_FD
    if [ $? -ne 0 ] ; then
      echo "WARNING: Could not set maximum file descriptor limit: $MAX_FD"
    fi
  else
    echo "WARNING: Could not query maximum file descriptor limit: $MAX_FD_LIMIT"
  fi
fi

# For Darwin, add options to specify how the application appears in the dock
if $darwin ; then
  GRADLE_OPTS="$GRADLE_OPTS \"-Xdock:name=Gradle\" \"-Xdock:icon=$APP_HOME/media/gradle.icns\""
fi

# Process the input command line to add default JVM options
processArgs() {
  local arg
  for arg in "$@"; do
    case "$arg" in
      --exec-wrapper)
        # Special marker for Gradle process fork/exec. This is not a JVM argument.
        echo "$arg"
        ;;
      -D*|-X*|-ea|-da)
        # JVM options
        echo "$arg"
        ;;
      *)
        # Not a JVM option
        ;;
    esac
  done
}

# Collect all arguments for the java command, following the shell quoting and substitution rules
eval set -- "$DEFAULT_JVM_OPTS $JAVA_OPTS $(processArgs "$@") $GRADLE_OPTS"

# Determine Gradle command
if [ "$cygwin" = "true" -o "$msys" = "true" ] ; then
  GRADLE_CMD="$APP_HOME/gradle.bat"
else
  GRADLE_CMD="$APP_HOME/gradle"
fi

# Pass the remaining arguments to Gradle
exec "$JAVACMD" "$@" -classpath "$APP_HOME/gradle/wrapper/gradle-wrapper.jar" org.gradle.wrapper.GradleWrapperMain "$@"
