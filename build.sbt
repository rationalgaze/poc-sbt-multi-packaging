import sbt.Keys.mappings

name := "poc-multi-project"

version := "0.1"

scalaVersion := "2.11.8"

lazy val common = project
  .in(file("common"))
  .enablePlugins(UniversalPlugin)
  .settings(
    name := "common",
    assemblySettings,
    zipSettings,
    mappings in Universal += {
      val oozie = (sourceDirectory.value).getParentFile / "oozie" / "somewf_file.xml"
      oozie -> "oozie/file.xml"
    },
    mappings in Universal += {
      val jar = target.value / "scala-2.12" / "common.jar"
      jar -> "jar/common.jar"
    }
  )

lazy val module1 = project
  .in(file("module1"))
  .enablePlugins(UniversalPlugin)
  .settings(
    name := "module1",
    assemblySettings,
    zipSettings,
    mappings in Universal += {
      val oozie = sourceDirectory.value.getParentFile / "oozie" / "config.xml"
      oozie -> "oozie/config.xml"
    },
    mappings in Universal += {
      val jar = target.value / "scala-2.12" / "module1.jar"
      jar -> "jar/module1.jar"
    }
  )

def zipSettings = Seq(
  packageName in Universal := packageName.value
)

lazy val assemblySettings = Seq(
  assemblyOption in assembly := (assemblyOption in assembly).value.copy(includeScala = false),
  assemblyJarName in assembly := name.value + ".jar",
  assemblyMergeStrategy in assembly := {
    case PathList("META-INF", xs @ _*) => MergeStrategy.discard
    case _                             => MergeStrategy.first
  }
)