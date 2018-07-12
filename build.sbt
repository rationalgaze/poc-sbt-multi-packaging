import sbt.Keys.mappings
import NativePackagerHelper._

name := "poc-multi-project"

version := "0.1"

scalaVersion in ThisBuild := "2.11.8"

// common files, scripts, xmls
lazy val common = project
  .in(file("common"))
  .enablePlugins(UniversalPlugin)
  .settings(
    name := "common",
    zipSettings,
    mappings in Universal ++= directory("common/build"),
    mappings in Universal ++= directory("common/config"),
    mappings in Universal ++= directory("common/livraison")
  )
  // do not use assembly this project
  .disablePlugins(AssemblyPlugin)

// first scala/spark project with oozie folder containing work flow xml
lazy val module1 = project
  .in(file("module1"))
  .enablePlugins(UniversalPlugin)
  .settings(
    name := "module1",
    assemblySettings,
    zipSettings,
    mappings in Universal ++= directory("module1/oozie"),
    mappings in Universal ++= directory("module1/target/jar")
  )

// first scala/spark project with oozie folder containing work flow xml
lazy val module2 = project
  .in(file("module2"))
  .enablePlugins(UniversalPlugin)
  .settings(
    name := "module2",
    assemblySettings,
    zipSettings,
    mappings in Universal ++= directory("module2/oozie"),
    mappings in Universal ++= directory("module2/target/jar")
)


// DEPENDENCIES
lazy val dependencies = new {
  val sparkVersion = "2.1.0"

  val oozie = "org.apache.oozie" % "oozie-client" % "4.1.0"
  val spark = "org.apache.spark" %% "spark-core" % sparkVersion % "provided" withSources() withJavadoc()
  val sparkSql = "org.apache.spark" %% "spark-sql" % sparkVersion % "provided" withSources() withJavadoc()
}

lazy val commonDependencies = Seq(
  dependencies.oozie,
  dependencies.spark,
  dependencies.sparkSql
)

// SETTINGS
def zipSettings = Seq(
  packageName in Universal := packageName.value
)

lazy val assemblySettings = Seq(
  // remove scala .jar
  assemblyOption in assembly := (assemblyOption in assembly).value.copy(includeScala = false),
  assemblyOutputPath in assembly := file(s"${name.value}/target/jar/${name.value}.jar"),
  assemblyMergeStrategy in assembly := {
    case PathList("META-INF", xs @ _*) => MergeStrategy.discard
    case _                             => MergeStrategy.first
  }
)
