$(document).ready(function(){
  $("#input").keyup(function(){

    var queryString = $('#input').val();
    var hostname = window.location.hostname;
    var port = window.location.port;
    var url = "http://" +hostname+ ":" +port+ "/api?sq=" +queryString
    console.log(url)
    $.get(url, function(response){
        console.log(response)
        $("#input").html(queryString);
        var response_len = response.results.length
        console.log(response_len)

        var result = ""
        for (let i = 0; i < response_len; i++) {

           var wikidataurl = response.results[i].wikidataurl
           var name = response.results[i].name
           var description = response.results[i].description

           result = result + '<li><a href="'+ wikidataurl + '" style="text-decoration:none;">'+ name + '</a><sub>' + description + '</sub></li>'
        }
        $("#result").html(result);
    });
  });
});