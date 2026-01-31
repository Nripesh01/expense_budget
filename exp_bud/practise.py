# def dispatch(self, request, *args, **kwargs): # dispatch is a DRF/Django method that receives every HTTP request 
        # first and then routes that request to the correct handler method (get(), post(), put(), patch(), delete(), etc.).
        # Overriding dispatch() lets you do pre-processing before any HTTP method runs, like fetching a group and 
        # storing it in self.group for later use in get(), post(), or serializers. 
       # self.group = get_object_or_404(Group, id=kwargs['group_id'], members=self.request.user)
                                              # kwargs['group_id'], get the group ID from the URL
        #return super().dispatch(request, *args, **kwargs)
        # call the parent in dispatch() for routing, authentication, permissions,etc., 
        # while still doing custom pre-processing before the request reaches the handler method
    
  #  def get_queryset(self):
    #    return Category.objects.filter(group=self.group).order_by('name')
    
  #  def perform_create(self, serializer):
   #     serializer.save(group=self.group)

