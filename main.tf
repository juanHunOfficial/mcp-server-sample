variable "region" { default = "us-east-1" }
variable "instance_type" { default = "t3.micro" }
 
provider "aws" {
  region = var.region
}
 
resource "aws_vpc" "main" {
  cidr_block = "10.0.0.0/16"
}
 
resource "aws_subnet" "subnet1" {
  vpc_id     = aws_vpc.main.id
  cidr_block = "10.0.1.0/24"
}
 
resource "aws_instance" "web" {
  ami           = "ami-123456"
  instance_type = var.instance_type
  subnet_id     = aws_subnet.subnet1.id
}
 
output "web_ip" {
  value = aws_instance.web.public_ip
}
